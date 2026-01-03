import yfinance as yf
import pandas as pd
import os
import google.generativeai as genai
import time
from datetime import datetime

# A list of ~200 popular/liquid US ETFs
ETF_TICKERS = [
    "SPY", "IVV", "VOO", "VTI", "QQQ", "VEA", "VTV", "IEFA", "BND", "AGG",
    "VUG", "IJR", "IWF", "IJH", "VIG", "GLD", "VWO", "VXUS", "IWM", "VNQ",
    "BSV", "VGT", "CSPS", "VCIT", "TIP", "BNDX", "LQD", "SCHX", "SCHD", "VCSH",
    "IVW", "XLK", "SPLG", "XLE", "XLF", "ITOT", "SCHF", "MBB", "IEMG", "VGK",
    "GOVT", "SHV", "TLT", "XLV", "MUB", "IGSB", "SCHB", "XLY", "VMBS", "IEF",
    "EFA", "VBR", "VV", "IXUS", "USMV", "BIL", "SCHA", "XLC", "VGSH", "VTEB",
    "DIA", "SHY", "EMB", "RSP", "SDY", "HYG", "XLI", "IWB", "JPST", "GDX",
    "XLP", "SCHP", "IAU", "SLV", "MDY", "SGOV", "IUSB", "SPYG", "VHT", "BIV",
    "ESGU", "QUAL", "IGIB", "SPYV", "EFV", "VTIP", "SPSB", "IWR", "ACWI", "VYM",
    "XLB", "DVY", "STIP", "COWZ", "MTUM", "VLUE", "XOP", "KRE", "XBI", "SMH",
    "ARKK", "ARKG", "TAN", "ICLN", "PBW", "LIT", "URA", "BOTZ", "CIBR", "SKYY",
    "HACK", "IPAY", "FINX", "SNSR", "ROBO", "ARKF", "ARKW", "BLOK", "GBTC", "BITO",
    "GLDM", "PPLT", "PALL", "SLV", "USO", "UNG", "DBC", "PDBC", "CORN", "WEAT",
    "SOXX", "SOXL", "SOXS", "TQQQ", "SQQQ", "SPXU", "UPRO", "LABU", "LABD", "YINN",
    "YANG", "BOIL", "KOLD", "NUGT", "DUST", "JNUG", "JDST", "UVXY", "VIXY", "SVXY",
    "TMF", "TMV", "ERX", "ERY", "FAS", "FAZ", "TECL", "TECS", "DRN", "DRV",
    "NRGU", "NRGD", "GUSH", "DRIP", "NAIL", "CURE", "TZA", "TNA", "URTY", "SRTY",
    "MIDU", "SPXS", "SPXL", "SSO", "SDS", "QID", "QLD", "PSQ", "DOG", "SH",
    "EFX", "EEM", "FXI", "MCHI", "KWEB", "EWJ", "EWZ", "INDA", "RSX", "EWY",
    "EWT", "EWG", "EWU", "EWL", "EWC", "EWA", "EWW", "TUR", "THD", "EPHE",
    "EZA", "ECH", "EPU", "GREK", "NORW", "EDEN", "EFNL", "ENZL", "EIDO", "VNM"
]

def configure_genai():
    """Configures the Google Generative AI API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Skipping AI analysis.")
        return False
    genai.configure(api_key=api_key)
    return True

def analyze_mover(ticker, change, is_configured):
    """
    Uses Gemini to analyze why an ETF moved.
    """
    if not is_configured:
        return "Analysis unavailable (API key missing)."

    model = genai.GenerativeModel('gemini-1.5-flash')
    direction = "up" if change > 0 else "down"
    prompt = (
        f"The ETF {ticker} is {direction} by {abs(change):.2f}% in the last trading session. "
        f"Identify what this ETF tracks (sector/commodity/strategy) and provide a single, concise sentence "
        f"explaining the likely reason for this move based on recent market trends (e.g., sector rotation, interest rates, commodity prices). "
        f"If unknown, mention it tracks general volatility."
    )
    
    try:
        response = model.generate_content(prompt)
        time.sleep(4) # Rate limit protection (15 RPM = 4s/req)
        return response.text.strip()
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return f"Analysis unavailable due to error: {e}"

def get_etf_movers():
    print(f"Fetching data for {len(ETF_TICKERS)} ETFs...")
    
    # Download batch data for 1 day
    data = yf.download(ETF_TICKERS, period="5d", progress=False)
    
    # Calculate % change from the last closing price
    # 'Close' is a DataFrame with tickers as columns
    closes = data['Close']
    
    if closes.empty:
        return [], []

    # Get the latest two days to calculate change
    latest_close = closes.iloc[-1]
    prev_close = closes.iloc[-2]
    
    percent_changes = ((latest_close - prev_close) / prev_close) * 100
    
    # Drop NaNs (tickers that might have failed)
    percent_changes = percent_changes.dropna()
    
    # Sort
    sorted_changes = percent_changes.sort_values(ascending=False)
    
    top_gainers = sorted_changes.head(5)
    top_losers = sorted_changes.tail(5) # These are negative, so smallest (most negative) are at the end
    
    # Convert to list of dicts for easier processing
    gainers_list = [{'ticker': t, 'change': v, 'price': latest_close[t]} for t, v in top_gainers.items()]
    losers_list = [{'ticker': t, 'change': v, 'price': latest_close[t]} for t, v in top_losers.items()]
    
    # Re-sort losers to be "biggest loser first" (most negative first)
    losers_list.sort(key=lambda x: x['change'])
    
    return gainers_list, losers_list

def generate_markdown_report(gainers, losers, gainers_analysis, losers_analysis):
    report_date = datetime.now().strftime("%Y-%m-%d")
    report = f"# Daily ETF Movers Watch - {report_date}\n\n"
    
    report += "## Top 5 ETF Gainers\n"
    for i, item in enumerate(gainers):
        report += (
            f"### {i+1}. {item['ticker']}\n"
            f"- **Price:** ${item['price']:.2f}\n"
            f"- **Change:** +{item['change']:.2f}%\n"
            f"- **Analysis:** {gainers_analysis[i]}\n\n")

    report += "## Top 5 ETF Losers\n"
    for i, item in enumerate(losers):
        report += (
            f"### {i+1}. {item['ticker']}\n"
            f"- **Price:** ${item['price']:.2f}\n"
            f"- **Change:** {item['change']:.2f}%\n"
            f"- **Analysis:** {losers_analysis[i]}\n\n")
    return report

def main():
    is_genai_configured = configure_genai()
    
    try:
        gainers, losers = get_etf_movers()
    except Exception as e:
        print(f"Error fetching ETF data: {e}")
        return

    if not gainers:
        print("No ETF data found.")
        return

    print("Analyzing top gainers...")
    gainers_analysis = []
    for item in gainers:
        print(f"  - Analyzing {item['ticker']}...")
        analysis = analyze_mover(item['ticker'], item['change'], is_genai_configured)
        gainers_analysis.append(analysis)

    print("Analyzing top losers...")
    losers_analysis = []
    for item in losers:
        print(f"  - Analyzing {item['ticker']}...")
        analysis = analyze_mover(item['ticker'], item['change'], is_genai_configured)
        losers_analysis.append(analysis)
    
    report_content = generate_markdown_report(
        gainers, losers, gainers_analysis, losers_analysis
    )
    
    # Save simply as index.md for GitHub Pages immediate rendering
    with open("index.md", "w") as f:
        f.write(report_content)
    print("\nReport saved to index.md")

if __name__ == "__main__":
    main()
