"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Navigation */}
      <nav className="flex justify-between items-center px-8 py-4 border-b border-slate-700/50">
        <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
          NusaTrade
        </div>
        <div className="flex gap-4">
          <Link href="/login">
            <button className="px-4 py-2 text-slate-300 hover:text-white transition-colors">
              Login
            </button>
          </Link>
          <Link href="/register">
            <button className="px-4 py-2 bg-gradient-to-r from-blue-500 to-emerald-500 text-white rounded-lg hover:opacity-90 transition-opacity font-medium">
              Get Started
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center px-8 py-24 text-center">
        <div className="inline-block px-4 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-full text-blue-400 text-sm font-medium mb-6">
          🚀 AI-Powered Trading Platform
        </div>

        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
          Trade Smarter with{" "}
          <span className="bg-gradient-to-r from-blue-400 via-emerald-400 to-blue-400 bg-clip-text text-transparent">
            AI Technology
          </span>
        </h1>

        <p className="text-xl text-slate-400 max-w-2xl mb-10">
          Platform trading forex dengan AI supervisor, ML bots, dan backtesting canggih.
          Maksimalkan profit Anda dengan teknologi terdepan.
        </p>

        <div className="flex gap-4">
          <Link href="/register">
            <button className="px-8 py-3 bg-gradient-to-r from-blue-500 to-emerald-500 text-white rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-blue-500/25 transition-all">
              Mulai Gratis
            </button>
          </Link>
          <Link href="/dashboard">
            <button className="px-8 py-3 bg-slate-700/50 text-white rounded-xl font-semibold text-lg border border-slate-600 hover:bg-slate-700 transition-colors">
              Lihat Demo
            </button>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="px-8 py-20">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-8">
          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700/50 hover:border-blue-500/50 transition-colors">
            <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              🤖
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">AI Supervisor</h3>
            <p className="text-slate-400">
              AI yang mengawasi dan memberikan insight real-time untuk keputusan trading Anda.
            </p>
          </div>

          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700/50 hover:border-emerald-500/50 transition-colors">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              📈
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">ML Trading Bots</h3>
            <p className="text-slate-400">
              Bot trading berbasis Machine Learning yang belajar dan beradaptasi dengan pasar.
            </p>
          </div>

          <div className="p-6 bg-slate-800/50 rounded-2xl border border-slate-700/50 hover:border-purple-500/50 transition-colors">
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center text-2xl mb-4">
              🔬
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Advanced Backtesting</h3>
            <p className="text-slate-400">
              Uji strategi trading Anda dengan data historis sebelum live trading.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="px-8 py-16 bg-slate-800/30">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-4xl font-bold text-white mb-1">10K+</div>
            <div className="text-slate-400">Active Traders</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-1">$50M+</div>
            <div className="text-slate-400">Trading Volume</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-1">99.9%</div>
            <div className="text-slate-400">Uptime</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-1">24/7</div>
            <div className="text-slate-400">AI Monitoring</div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-8 py-20 text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
          Siap Mulai Trading?
        </h2>
        <p className="text-slate-400 mb-8 max-w-xl mx-auto">
          Bergabung dengan ribuan trader yang sudah menggunakan NusaTrade untuk trading yang lebih cerdas.
        </p>
        <Link href="/register">
          <button className="px-8 py-3 bg-gradient-to-r from-blue-500 to-emerald-500 text-white rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-blue-500/25 transition-all">
            Daftar Sekarang - Gratis!
          </button>
        </Link>
      </section>

      {/* Footer */}
      <footer className="px-8 py-8 border-t border-slate-700/50 text-center text-slate-500 text-sm">
        © 2024 NusaTrade. All rights reserved.
      </footer>
    </div>
  );
}
