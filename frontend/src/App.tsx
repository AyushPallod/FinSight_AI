import { useState, useEffect } from 'react'
import { 
  Activity, 
  Cpu, 
  Database, 
  CheckCircle2, 
  AlertCircle, 
  Terminal,
  Layers,
  Sparkles
} from 'lucide-react'
import './App.css'

interface HealthStatus {
  status: string
  project: string
  ollama_base_url: string
  qdrant_host: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const checkConnection = () => {
    setLoading(true)
    setError(null)
    fetch('/api/v1/health')
      .then(res => {
        if (!res.ok) throw new Error('Backend healthcheck failed')
        return res.json()
      })
      .then((data: HealthStatus) => {
        setHealth(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setError('Could not connect to FastAPI backend at /api/v1/health')
        setHealth(null)
        setLoading(false)
      })
  }

  useEffect(() => {
    checkConnection()
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Background Glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full filter blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full filter blur-3xl pointer-events-none"></div>

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md px-8 py-4 flex justify-between items-center z-10">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Layers className="h-5 w-5 text-slate-950" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
              FinSight AI
            </h1>
            <p className="text-[10px] text-emerald-400/80 font-mono tracking-widest uppercase">System Initialization</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <span className="flex h-2.5 w-2.5 relative">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${health ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${health ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
          </span>
          <span className="text-xs font-medium text-slate-400">
            {health ? 'Backend Live' : 'Backend Offline'}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-12 flex flex-col md:flex-row gap-8 items-stretch z-10">
        
        {/* Left column: Overview and Status */}
        <div className="flex-1 flex flex-col space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col space-y-4 shadow-xl">
            <div className="inline-flex items-center space-x-2 bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full text-xs font-medium w-fit border border-emerald-500/20">
              <Sparkles className="h-3 w-3" />
              <span>Phase 1 Sandbox Active</span>
            </div>
            
            <h2 className="text-3xl font-extrabold tracking-tight font-display bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">
              Financial Document Intelligence RAG
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed">
              Welcome to the initialization checkpoint for FinSight AI. The monorepo layout has been established, the Python virtual environment configured, and Tailwind CSS v4 loaded successfully.
            </p>

            {/* Status Grid */}
            <div className="grid grid-cols-2 gap-4 pt-4">
              {/* API status */}
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">FastAPI Backend</span>
                  {health ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-rose-400" />
                  )}
                </div>
                <div className="mt-4">
                  <p className="text-xs font-mono text-slate-500">/api/v1</p>
                  <p className="text-sm font-semibold mt-1">{health ? 'Connected' : 'Offline'}</p>
                </div>
              </div>

              {/* Ollama status */}
              <div className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400 font-medium">Ollama Service</span>
                  {health ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-slate-600" />
                  )}
                </div>
                <div className="mt-4">
                  <p className="text-xs font-mono text-slate-500">
                    {health ? health.ollama_base_url : 'http://localhost:11434'}
                  </p>
                  <p className="text-sm font-semibold mt-1">
                    {health ? 'Ready (llama3.2)' : 'Waiting...'}
                  </p>
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-300 p-4 rounded-xl text-xs flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold">Backend Connection Issue</p>
                  <p className="mt-1">{error}</p>
                  <p className="mt-2 text-slate-400">Please start the FastAPI server using:</p>
                  <code className="block mt-1 font-mono bg-slate-950 p-2 rounded border border-slate-800 text-[10px] select-all">
                    cd backend; .venv\Scripts\uvicorn app.main:app --reload
                  </code>
                </div>
              </div>
            )}

            <button 
              onClick={checkConnection}
              disabled={loading}
              className="mt-2 w-full py-2.5 px-4 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-slate-950 font-bold rounded-xl text-sm transition-all duration-200 shadow-lg shadow-emerald-500/15 flex items-center justify-center space-x-2 cursor-pointer"
            >
              {loading ? (
                <div className="h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Refresh Connection Status</span>
                  <Activity className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right column: Build Roadmap Progress */}
        <div className="flex-1 flex flex-col">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col space-y-4 shadow-xl h-full justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Terminal className="h-5 w-5 text-emerald-400" />
                <h3 className="text-lg font-bold font-display text-slate-200">Phase 1 Checklist</h3>
              </div>

              <div className="space-y-4">
                {/* Step 1 */}
                <div className="flex items-start space-x-3">
                  <div className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 border border-emerald-500/30">
                    ✓
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">Init Repo & Directory Structure</h4>
                    <p className="text-xs text-slate-400 mt-0.5">Created backend FastAPI base, frontend Vite React app, and configuration templates.</p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="flex items-start space-x-3 opacity-60">
                  <div className="h-5 w-5 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 border border-slate-700">
                    2
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300">Document Ingestion Pipeline</h4>
                    <p className="text-xs text-slate-400 mt-0.5">PyMuPDF text extractor, python-docx, OCR fallback logic (Tesseract).</p>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="flex items-start space-x-3 opacity-60">
                  <div className="h-5 w-5 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 border border-slate-700">
                    3
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300">Qdrant & Embeddings Generation</h4>
                    <p className="text-xs text-slate-400 mt-0.5">BGE-M3 models embeddings storage in Qdrant Vector database.</p>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="flex items-start space-x-3 opacity-60">
                  <div className="h-5 w-5 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 border border-slate-700">
                    4
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300">Hybrid Search & Citation Grounding</h4>
                    <p className="text-xs text-slate-400 mt-0.5">Reciprocal Rank Fusion (BM25 + Dense) and inline citations LLM prompt generation.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-slate-800/80 pt-6 mt-6 flex flex-col space-y-3">
              <div className="flex items-center space-x-2 text-xs text-slate-400">
                <Database className="h-4 w-4 text-teal-400" />
                <span>Vector Database: Qdrant (Host: localhost:6333)</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-slate-400">
                <Cpu className="h-4 w-4 text-emerald-400" />
                <span>LLM Engine: Ollama Local (Model: llama3.2)</span>
              </div>
            </div>
          </div>
        </div>

      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-slate-900 bg-slate-950/80 text-center text-xs text-slate-500 z-10">
        <p>© {new Date().getFullYear()} FinSight AI build sandbox. Built with FastAPI, Vite, React and Tailwind CSS v4.</p>
      </footer>
    </div>
  )
}

export default App
