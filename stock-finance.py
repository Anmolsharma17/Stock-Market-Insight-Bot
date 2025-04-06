import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
from openai import OpenAI  # Import the OpenAI module

# DeepSeek API integration using OpenAI client
class DeepSeekAPI:
    def __init__(self, api_key):
        # Initialize the OpenAI client with DeepSeek's base URL and API key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def generate_insight(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a financial analyst providing detailed stock insights."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                max_tokens=200,  # Added for response length control
                temperature=0.7  # Added for response consistency
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: DeepSeek API request failed - {str(e)}"

# Initialize DeepSeek API with your provided key
DEEPSEEK_API_KEY = "sk-dad5bb2d05c64d7b9c8eb7c28bac0384"
deepseek = DeepSeekAPI(DEEPSEEK_API_KEY)

class StockInsightBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Insight Bot with DeepSeek AI")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0f172a")
        self.root.resizable(False, False)

        self.portfolio = {}
        self.running = True

        self.setup_styles()
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.container, width=280, style="Sidebar.TFrame")
        self.sidebar.pack(side="left", fill="y", padx=(0, 2))

        self.content = ttk.Frame(self.container, style="Content.TFrame")
        self.content.pack(side="right", fill="both", expand=True)

        self.setup_sidebar()
        self.setup_content()

        self.thread = threading.Thread(target=self.update_prices, daemon=True)
        self.thread.start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Sidebar.TFrame", background="#1e293b")
        style.configure("Content.TFrame", background="#0f172a")
        
        style.configure("TButton", 
                       background="#3b82f6",
                       foreground="white",
                       font=("Segoe UI", 12, "bold"),
                       padding="12 20",
                       borderwidth=0,
                       relief="flat")
        style.map("TButton",
                 background=[("active", "#2563eb"), ("hover", "#60a5fa")])
        
        style.configure("Small.TButton",
                       font=("Segoe UI", 10),
                       padding="6 12",
                       background="#475569",
                       foreground="white")
        style.map("Small.TButton",
                 background=[("active", "#334155"), ("hover", "#64748b")])
        
        style.configure("Card.TFrame", 
                       background="#1e293b",
                       borderwidth=1,
                       relief="solid",
                       bordercolor="#334155",
                       padding=16)
        
        style.configure("HoverCard.TFrame",
                       background="#1e293b",
                       borderwidth=1,
                       relief="solid",
                       bordercolor="#60a5fa",
                       padding=16)
        
        style.configure("PortfolioTicker.TLabel", 
                       font=("Segoe UI", 12, "bold"), 
                       foreground="#93c5fd")
        style.configure("PortfolioPrice.TLabel", 
                       font=("Segoe UI", 11), 
                       foreground="#94a3b8")
        
        style.configure("TLabel",
                       background="#0f172a",
                       foreground="#e2e8f0",
                       font=("Segoe UI", 11))
        
        style.configure("Title.TLabel",
                       font=("Segoe UI", 18, "bold"),
                       foreground="#dbeafe",
                       padding=(0, 10))
        
        style.configure("RegNo.TLabel",
                       font=("Segoe UI", 9),
                       foreground="#94a3b8",
                       background="#0f172a")

    def setup_sidebar(self):
        ttk.Label(self.sidebar, 
                 text="Stock Dashboard",
                 style="Title.TLabel").pack(pady=(20, 30), padx=16)

        input_card = ttk.Frame(self.sidebar, style="Card.TFrame")
        input_card.pack(fill="x", padx=16, pady=(0, 20))
        ttk.Label(input_card, text="Stock Ticker:").pack(pady=(0, 8))
        self.ticker_entry = ttk.Entry(input_card, 
                                    font=("Segoe UI", 12),
                                    justify="center")
        self.ticker_entry.pack(fill="x", padx=8)

        actions = [
            ("Analyze Stock", self.analyze_stock),
            ("View Chart", self.plot_stock),
            ("Get Insight", self.get_insight),
            ("Buy/Sell Advice", self.get_buy_sell_advice),
            ("Add to Portfolio", self.add_to_portfolio)
        ]
        for text, command in actions:
            btn = ttk.Button(self.sidebar, text=text, command=command)
            btn.pack(pady=8, padx=16, fill="x")

        ttk.Label(self.sidebar, 
                 text="Portfolio",
                 font=("Segoe UI", 14, "bold"),
                 foreground="#dbeafe").pack(pady=(20, 10))
        self.portfolio_frame = ttk.Frame(self.sidebar)
        self.portfolio_frame.pack(fill="x", padx=16)
        self.update_portfolio_display()

    def setup_content(self):
        header_card = ttk.Frame(self.content, style="Card.TFrame")
        header_card.pack(fill="x", padx=24, pady=(24, 16))
        
        header_frame = ttk.Frame(header_card)
        header_frame.pack(fill="x", padx=16)
        ttk.Label(header_frame, 
                 text="Stock Insights",
                 style="Title.TLabel").pack(side="left")
        ttk.Label(header_frame,
                 text="Reg Nos: 12300914, 12309825, 12306419",
                 style="RegNo.TLabel").pack(side="right", pady=(5, 0))

        content_grid = ttk.Frame(self.content)
        content_grid.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self.info_pane = ttk.Frame(content_grid, style="Card.TFrame")
        self.info_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.chart_pane = ttk.Frame(content_grid, style="Card.TFrame")
        self.chart_pane.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        content_grid.columnconfigure(0, weight=1)
        content_grid.columnconfigure(1, weight=2)
        content_grid.rowconfigure(0, weight=1)

        self.info_text = tk.Text(self.info_pane, 
                                height=20, 
                                width=40,
                                bg="#1e293b",
                                fg="#e2e8f0",
                                font=("Segoe UI", 12),
                                wrap="word",
                                borderwidth=0,
                                padx=16,
                                pady=12)
        self.info_text.pack(fill="both", expand=True)

    def get_stock_data(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1mo")
            if df.empty:
                return None
            return df
        except:
            return None

    def analyze_stock(self):
        ticker = self.ticker_entry.get().upper()
        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol!")
            return

        df = self.get_stock_data(ticker)
        if df is None:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: Could not fetch data for {ticker}")
            return

        current_price = df['Close'].iloc[-1]
        avg_price = df['Close'].mean()
        price_std = df['Close'].std()
        volume_avg = df['Volume'].mean()
        sma_5 = df['Close'].rolling(window=5).mean().iloc[-1]

        prompt = (
            f"Analyze the stock {ticker} with current price ${current_price:.2f}, "
            f"30-day average ${avg_price:.2f}, volatility ${price_std:.2f}, "
            f"average volume {volume_avg:.0f} shares, and 5-day SMA ${sma_5:.2f}. "
            f"Provide a detailed analysis."
        )
        deepseek_insight = deepseek.generate_insight(prompt)

        analysis = (
            f"Stock Analysis - {ticker}\n"
            f"------------------------\n"
            f"Current Price: ${current_price:.2f}\n"
            f"30-day Avg: ${avg_price:.2f}\n"
            f"Volatility: ${price_std:.2f}\n"
            f"Avg Volume: {volume_avg:.0f} shares\n"
            f"5-day SMA: ${sma_5:.2f}\n"
            f"Trend: {'Up' if current_price > sma_5 else 'Down'}\n"
            f"\nDeepSeek AI Insight:\n{deepseek_insight}"
        )
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, analysis)

    def plot_stock(self):
        ticker = self.ticker_entry.get().upper()
        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol!")
            return

        df = self.get_stock_data(ticker)
        if df is None:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: Could not plot data for {ticker}")
            return

        for widget in self.chart_pane.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        ax.plot(df.index, df['Close'], label='Price', color='#60a5fa', linewidth=2)
        ax.plot(df.index, df['Close'].rolling(window=5).mean(), 
                label='5-day SMA', color='#f97316', linewidth=2)
        
        ax.set_title(f'{ticker} Price History', color='#e2e8f0', fontweight='bold')
        ax.set_xlabel('Date', color='#94a3b8')
        ax.set_ylabel('Price ($)', color='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#e2e8f0')
        ax.grid(True, alpha=0.2, color='#475569')
        ax.set_facecolor('#0f172a')
        fig.set_facecolor('#0f172a')
        ax.tick_params(colors='#94a3b8')
        plt.xticks(rotation=45, ha='right')

        canvas = FigureCanvasTkAgg(fig, master=self.chart_pane)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def get_insight(self):
        ticker = self.ticker_entry.get().upper()
        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol!")
            return

        df = self.get_stock_data(ticker)
        if df is None:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: Could not fetch data for {ticker}")
            return

        current_price = df['Close'].iloc[-1]
        sma_5 = df['Close'].rolling(window=5).mean().iloc[-1]
        rsi = self.calculate_rsi(df)

        prompt = (
            f"Provide a detailed insight for {ticker} with RSI {rsi:.1f}, "
            f"current price ${current_price:.2f}, and 5-day SMA ${sma_5:.2f}. "
            f"Include market sentiment if possible."
        )
        deepseek_insight = deepseek.generate_insight(prompt)

        insight = (
            f"Insight for {ticker}\n------------------------\n"
            f"RSI (14-day): {rsi:.1f}\n"
            f"Current vs SMA: {((current_price / sma_5 - 1) * 100):.1f}%\n"
            f"\nDeepSeek AI Insight:\n{deepseek_insight}"
        )
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, insight)

    def get_buy_sell_advice(self):
        ticker = self.ticker_entry.get().upper()
        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol!")
            return

        df = self.get_stock_data(ticker)
        if df is None:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: Could not fetch data for {ticker}")
            return

        current_price = df['Close'].iloc[-1]
        sma_5 = df['Close'].rolling(window=5).mean().iloc[-1]
        rsi = self.calculate_rsi(df)
        volatility = df['Close'].std() / df['Close'].mean() * 100

        prompt = (
            f"Provide buy/sell advice for {ticker} with RSI {rsi:.1f}, "
            f"current price ${current_price:.2f}, 5-day SMA ${sma_5:.2f}, "
            f"and volatility {volatility:.1f}%. Be conversational and detailed."
        )
        deepseek_advice = deepseek.generate_insight(prompt)

        advice = (
            f"Buy/Sell Advice for {ticker}\n------------------------\n"
            f"Metrics:\nRSI (14-day): {rsi:.1f}\n"
            f"Current vs SMA: {((current_price / sma_5 - 1) * 100):.1f}%\n"
            f"Volatility: {volatility:.1f}%\n"
            f"\nDeepSeek AI Advice:\n{deepseek_advice}"
        )
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, advice)

    def calculate_rsi(self, df, period=14):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    def add_to_portfolio(self):
        ticker = self.ticker_entry.get().upper()
        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol!")
            return
        if ticker not in self.portfolio:
            df = self.get_stock_data(ticker)
            if df is not None:
                self.portfolio[ticker] = {'price': df['Close'].iloc[-1], 'shares': 1}
                self.update_portfolio_display()
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, f"Added {ticker} to portfolio")

    def update_portfolio_display(self):
        for widget in self.portfolio_frame.winfo_children():
            widget.destroy()
        
        for ticker, data in self.portfolio.items():
            card = ttk.Frame(self.portfolio_frame, style="Card.TFrame")
            card.pack(fill="x", pady=6)
            
            card.bind("<Enter>", lambda e, c=card: c.configure(style="HoverCard.TFrame"))
            card.bind("<Leave>", lambda e, c=card: c.configure(style="Card.TFrame"))
            
            ttk.Label(card, 
                     text=ticker,
                     style="PortfolioTicker.TLabel").grid(row=0, column=0, sticky="w", padx=12)
            ttk.Label(card, 
                     text=f"${data['price']:.2f}",
                     style="PortfolioPrice.TLabel").grid(row=0, column=1, sticky="e", padx=12)
            
            btn_frame = ttk.Frame(card)
            btn_frame.grid(row=0, column=2, padx=8)
            ttk.Button(btn_frame, 
                      text="×", 
                      style="Small.TButton",
                      command=lambda t=ticker: self.remove_from_portfolio(t)).pack(side="left", padx=2)
            ttk.Button(btn_frame, 
                      text="R", 
                      style="Small.TButton",
                      command=lambda t=ticker: self.get_portfolio_insight(t)).pack(side="left", padx=2)
            
            card.columnconfigure(0, weight=1)
            card.columnconfigure(1, weight=0)
            card.columnconfigure(2, weight=0)

    def remove_from_portfolio(self, ticker):
        del self.portfolio[ticker]
        self.update_portfolio_display()

    def get_portfolio_insight(self, ticker):
        df = self.get_stock_data(ticker)
        if df is None:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, f"Error: Could not fetch data for {ticker}")
            return

        current_price = df['Close'].iloc[-1]
        sma_5 = df['Close'].rolling(window=5).mean().iloc[-1]
        rsi = self.calculate_rsi(df)

        prompt = (
            f"Provide a portfolio insight for {ticker} with RSI {rsi:.1f}, "
            f"current price ${current_price:.2f}, and 5-day SMA ${sma_5:.2f}. "
            f"Include market sentiment if possible."
        )
        deepseek_insight = deepseek.generate_insight(prompt)

        insight = (
            f"Portfolio Insight - {ticker}\n------------------------\n"
            f"RSI (14-day): {rsi:.1f}\n"
            f"Current vs SMA: {((current_price / sma_5 - 1) * 100):.1f}%\n"
            f"\nDeepSeek AI Insight:\n{deepseek_insight}"
        )
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, insight)

    def update_prices(self):
        while self.running:
            if self.portfolio:
                for ticker in self.portfolio.keys():
                    df = self.get_stock_data(ticker)
                    if df is not None:
                        self.portfolio[ticker]['price'] = df['Close'].iloc[-1]
                self.update_portfolio_display()
            time.sleep(60)

    def on_closing(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StockInsightBotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()