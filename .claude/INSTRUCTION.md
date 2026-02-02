# US Stock Backtesting System

This file provides an instruction to Claude Code (claude.ai/code) to work on this repository.

這個專案中，你將從0打造一個具備必要功能，且可靠、可擴展、可維護的美股回測系統，提供交易員評估策略可行性的一個服務。
這份文件告訴你：
- **Instruction:** 如何運用這份指引來實現該回測系統
- **Definition:** 名詞定義
- **Requirements:** 該回測系統背後的需求
- **Components:** 該回測系統需要具備的功能與模組

## Instruction
這是一份初級指引，它可能還不是很具體，可行性也未知，只是出於某種需求而被訂定。  
在閱讀這份指引時，你應該理解這個系統真正想解決的問題或需求是什麼。在開始實作該專案前，反覆向專案擁有者確認專案目的以及可行方案，直到你的提議確定是符合需求且可行的。  
在與專案擁有者溝通過程中，根據專案擁有者的回答與澄清，調整該文件的部分論述，使其更加具體、易讀。  
如果該指引有任何不合理或過時的論述，請主動提出疑慮並改善論述。  
待需求定義明確後，呼叫 full-stack-engineer 來完成整個專案的開發工作。

## Definition
- 專案擁有者(Project Owner): 該專案的擁有者或發起人
- 使用者(User): 使用該回測系統的對象，例如交易員

## Requirements
- 使用者能根據歷史數據與指標，自定義交易策略
- 使用者能輕易測試自定義的指標在過往歷史中的表現
- 該系統能提供內建的指標，協助使用者設計策略
- 該系統能提供各個美股歷史價格，以便交易員能在真實價格變化中回測交易策略
- 使用者能根據自身需求，添加自定義指標
- 支援多檔股票的投資組合回測(Portfolio-level backtesting)

## Tech Stack (已確認)
- **後端**: Python 3.11+ / FastAPI
- **前端**: React + Vite (TypeScript)
- **資料庫**: SQLite (輕量，零設定，適合單人使用的回測情境)
- **數據來源**: yfinance (主要) + CSV 匯入 (備用/自訂數據)
- **策略定義方式**: Python 程式碼 (使用者撰寫 Python class 繼承 Strategy 基底類別)
- **報告輸出**: Console 摘要 + HTML 視覺化報告 (含績效圖表與交易記錄表格)

## Components
- **數據管理(Data Manager)**: 能夠透過 yfinance 自動下載、或從 CSV 匯入歷史價格數據(OHLCV)，儲存至 SQLite，並提供查詢介面
- **策略定義介面(Strategy Interface)**: 一個統一的 Python 基底類別，使用者繼承後定義買賣規則，例如「當50日均線上穿200日均線時買入」。策略可操作多檔股票的投資組合。
- **指標庫(Indicator Library)**: 提供內建指標(SMA, EMA, RSI, MACD, Bollinger Bands 等)。在跑回測前，應先根據歷史 OHLCV 計算指標。使用者定義策略時無需自行計算內建指標，也可以自行擴充指標。
- **回測引擎(Backtest Engine)**: 按時間順序遍歷歷史數據，模擬策略執行，支援多檔股票同時交易，記錄每筆交易
- **績效計算(Performance Calculator)**: 計算總報酬率、年化報酬率、最大回撤、勝率、夏普比率等指標
- **交易記錄(Trade Recorder)**: 記錄每筆進出場時間、價格、持倉數量、標的股票
- **報告生成(Report Generator)**: 生成 Console 摘要 (快速瀏覽) 與 HTML 報告 (含權益曲線圖、回撤圖、交易記錄表格等視覺化內容)
- **Web API(REST API)**: FastAPI 提供後端 API，供前端呼叫，包含數據管理、回測執行、報告查詢等端點
- **Web 前端(Frontend)**: React + Vite 打造的互動式前端，提供股票數據瀏覽、策略管理、回測執行與結果視覺化