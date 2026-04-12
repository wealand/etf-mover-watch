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

# Motorsport & Luxury Watchlist
WATCHLIST_TICKERS = [
    "RACE",   # Ferrari
    "VWAGY",  # Volkswagen/Porsche/Audi
    "FWONK",  # Formula One Group
    "LVMUY",  # LVMH (Owners of TAG Heuer, Hublot, etc.)
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
    Uses Gemini to analyze why an asset moved.
    """
    if not is_configured:
        return "Analysis unavailable (API key missing)."

    # Using 2.0-flash for efficiency and reliability
    model = genai.GenerativeModel('gemini-2.0-flash')
    direction = "up" if change > 0 else "down"
    prompt = (
        f"The asset {ticker} is {direction} by {abs(change):.2f}% in the last trading session. "
        f"Identify what this asset represents (company/sector/commodity) and provide a single, concise sentence "
        f"explaining the likely reason for this move based on recent market trends. "
        f"If unknown, mention it tracks general market volatility."
    )
    
    try:
        response = model.generate_content(prompt)
        time.sleep(4) # Rate limit protection (15 RPM = 4s/req)
        return response.text.strip()
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return f"Analysis error: {str(e)[:100]}"

def get_market_data():
    all_tickers = list(set(ETF_TICKERS + WATCHLIST_TICKERS))
    print(f"Fetching data for {len(all_tickers)} assets...")
    
    data = yf.download(all_tickers, period="5d", progress=False)
    closes = data['Close']
    
    if closes.empty:
        return None, None, None

    latest_close = closes.iloc[-1]
    prev_close = closes.iloc[-2]
    percent_changes = ((latest_close - prev_close) / prev_close) * 100
    
    # Process ETFs
    etf_changes = percent_changes[ETF_TICKERS].dropna().sort_values(ascending=False)
    top_gainers = etf_changes.head(5)
    top_losers = etf_changes.tail(5)
    
    gainers_list = [{'ticker': t, 'change': v, 'price': latest_close[t]} for t, v in top_gainers.items()]
    losers_list = [{'ticker': t, 'change': v, 'price': latest_close[t]} for t, v in top_losers.items()]
    losers_list.sort(key=lambda x: x['change'])

    # Process Watchlist
    watchlist_list = []
    for t in WATCHLIST_TICKERS:
        if t in percent_changes:
            watchlist_list.append({'ticker': t, 'change': percent_changes[t], 'price': latest_close[t]})
    
    return gainers_list, losers_list, watchlist_list

def generate_markdown_report(gainers, losers, watchlist, g_analysis, l_analysis, w_analysis):
    report_date = datetime.now().strftime("%Y-%m-%d")
    report = f"# Daily Market Movers Watch - {report_date}\n\n"
    
    report += "## 📈 Top 5 ETF Gainers\n"
    for i, item in enumerate(gainers):
        report += (
            f"### {i+1}. {item['ticker']}\n"
            f"- **Price:** ${item['price']:.2f}\n"
            f"- **Change:** +{item['change']:.2f}%\n"
            f"- **Analysis:** {g_analysis[i]}\n\n")

    report += "## 📉 Top 5 ETF Losers\n"
    for i, item in enumerate(losers):
        report += (
            f"### {i+1}. {item['ticker']}\n"
            f"- **Price:** ${item['price']:.2f}\n"
            f"- **Change:** {item['change']:.2f}%\n"
            f"- **Analysis:** {l_analysis[i]}\n\n")

    if watchlist:
        report += "## 🏎️ Motorsport & Luxury Watchlist\n"
        for item in watchlist:
            analysis = w_analysis.get(item['ticker'], "No major move (>=2%) detected for detailed analysis.")
            report += (
                f"### {item['ticker']}\n"
                f"- **Price:** ${item['price']:.2f}\n"
                f"- **Change:** {item['change']:+.2f}%\n"
                f"- **Analysis:** {analysis}\n\n")
                
    return report

def generate_html_report(gainers, losers, watchlist, g_analysis, l_analysis, w_analysis):
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Market Movers - {report_date}</title>
        <style>
            :root {{
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --gainer: #22c55e;
                --loser: #ef4444;
                --accent: #38bdf8;
                --watchlist: #f59e0b;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                margin: 0;
                padding: 0;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 2rem;
            }}
            header {{
                text-align: center;
                margin-bottom: 3rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #334155;
            }}
            h1 {{
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
                background: linear-gradient(to right, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .date {{ color: var(--text-muted); font-size: 1.1rem; }}
            
            h2 {{
                font-size: 1.8rem;
                margin-top: 2rem;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .gainers-title {{ color: var(--gainer); }}
            .losers-title {{ color: var(--loser); }}
            .watchlist-title {{ color: var(--watchlist); }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-bottom: 3rem;
            }}
            .card {{
                background-color: var(--card-bg);
                border-radius: 0.75rem;
                padding: 1.5rem;
                border: 1px solid #334155;
                transition: transform 0.2s;
            }}
            .card:hover {{ transform: translateY(-4px); border-color: var(--accent); }}
            
            .ticker {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 0.25rem; }}
            .price {{ font-size: 1.1rem; color: var(--text-main); font-weight: 500; }}
            .change {{ font-weight: 700; font-size: 1.2rem; margin-bottom: 1rem; }}
            .change.up {{ color: var(--gainer); }}
            .change.down {{ color: var(--loser); }}
            
            .analysis-box {{
                background-color: rgba(15, 23, 42, 0.5);
                padding: 1rem;
                border-radius: 0.5rem;
                font-size: 0.95rem;
                border-left: 3px solid var(--accent);
            }}
            .watchlist-card {{ border-top: 2px solid var(--watchlist); }}
            .watchlist-card .analysis-box {{ border-left-color: var(--watchlist); }}
            
            footer {{
                text-align: center;
                margin-top: 4rem;
                padding-top: 2rem;
                border-top: 1px solid #334155;
                color: var(--text-muted);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Market Mover Watch</h1>
                <div class="date">{report_date} Report</div>
            </header>

            <h2 class="gainers-title">📈 Top ETF Gainers</h2>
            <div class="grid">
    """
    
    for i, item in enumerate(gainers):
        html_content += f"""
                <div class="card">
                    <div class="ticker">{item['ticker']}</div>
                    <div class="price">${item['price']:.2f}</div>
                    <div class="change up">+{item['change']:.2f}%</div>
                    <div class="analysis-box">{g_analysis[i]}</div>
                </div>
        """

    html_content += """
            </div>

            <h2 class="losers-title">📉 Top ETF Losers</h2>
            <div class="grid">
    """
    
    for i, item in enumerate(losers):
        html_content += f"""
                <div class="card">
                    <div class="ticker">{item['ticker']}</div>
                    <div class="price">${item['price']:.2f}</div>
                    <div class="change down">{item['change']:.2f}%</div>
                    <div class="analysis-box">{l_analysis[i]}</div>
                </div>
        """

    html_content += """
            </div>

            <h2 class="watchlist-title">🏎️ Motorsport & Luxury Watchlist</h2>
            <div class="grid">
    """
    
    for item in watchlist:
        analysis = w_analysis.get(item['ticker'], "No major move (>=2%) detected for analysis.")
        change_class = "up" if item['change'] > 0 else "down"
        html_content += f"""
                <div class="card watchlist-card">
                    <div class="ticker">{item['ticker']}</div>
                    <div class="price">${item['price']:.2f}</div>
                    <div class="change {change_class}">{item['change']:+.2f}%</div>
                    <div class="analysis-box">{analysis}</div>
                </div>
        """

    html_content += """
            </div>
            
            <footer>
                <p>AI-Powered Market Analysis Bot 🤖</p>
                <p><a href="https://buymeacoffee.com/icecapades" target="_blank" style="color: #ffdd00; text-decoration: none; font-weight: bold;">☕ Buy me a coffee</a></p>
            </footer>
        </div>
    </body>
    </html>
    """
    return html_content

def main():
    is_genai_configured = configure_genai()
    
    try:
        gainers, losers, watchlist = get_market_data()
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return

    if not gainers:
        print("No market data found.")
        return

    print("Analyzing top gainers...")
    g_analysis = []
    for item in gainers:
        print(f"  - Analyzing {item['ticker']}...")
        g_analysis.append(analyze_mover(item['ticker'], item['change'], is_genai_configured))

    print("Analyzing top losers...")
    l_analysis = []
    for item in losers:
        print(f"  - Analyzing {item['ticker']}...")
        l_analysis.append(analyze_mover(item['ticker'], item['change'], is_genai_configured))

    print("Checking watchlist for significant moves...")
    w_analysis = {}
    # Only analyze the top 2 biggest movers in watchlist if change > 2%
    significant_movers = [item for item in watchlist if abs(item['change']) >= 2.0]
    significant_movers.sort(key=lambda x: abs(x['change']), reverse=True)
    
    for item in significant_movers[:2]: # Max 2 additional calls to protect rate limits
        print(f"  - Analyzing watchlist mover {item['ticker']} ({item['change']:.2f}%)...")
        w_analysis[item['ticker']] = analyze_mover(item['ticker'], item['change'], is_genai_configured)
    
    report_content = generate_markdown_report(
        gainers, losers, watchlist, g_analysis, l_analysis, w_analysis
    )
    
    with open("index.md", "w") as f:
        f.write(report_content)
    print("\nReport saved to index.md")
    
    html_report = generate_html_report(
        gainers, losers, watchlist, g_analysis, l_analysis, w_analysis
    )
    with open("index.html", "w") as f:
        f.write(html_report)
    print("Visual dashboard saved to index.html")

if __name__ == "__main__":
    main()
