'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import { Send, Loader2, BarChart3 } from 'lucide-react'
import ForecastChart from './ForecastChart'

interface ForecastData {
  dates: string[]
  values: number[]
  lower_bound: number[]
  upper_bound: number[]
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  forecast?: ForecastData
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm PRISM AI. I can help you analyze sales patterns, detect trends, and forecast future sales.\n\nTry asking:\n• \"Show me products trending up\"\n• \"Find products with spikes\"\n• \"What products are volatile?\"\n• \"Show seasonal products\""
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const detectIntent = (msg: string): { type: string; params: Record<string, any> } => {
    const lower = msg.toLowerCase()
    
    if (lower.includes('forecast') || lower.includes('predict')) {
      const productMatch = msg.match(/(?:for|forecast|predict)\s+([A-Za-z\s]+?)(?:\s+for|\s+next|\s*$)/i)
      const horizonMatch = msg.match(/(\d+)\s*months?/i)
      return {
        type: 'forecast',
        params: {
          product_id: productMatch?.[1]?.trim().replace(/\s+/g, '_'),
          horizon: horizonMatch ? parseInt(horizonMatch[1]) : 6
        }
      }
    }
    
    if (lower.includes('run') && (lower.includes('analysis') || lower.includes('transform') || lower.includes('pipeline'))) {
      return { type: 'transform', params: {} }
    }
    
    return { type: 'query', params: {} }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const intent = detectIntent(input)
      let response: Message

      if (intent.type === 'forecast' && intent.params.product_id) {
        const res = await fetch('/api/forecast', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: intent.params.product_id, horizon: intent.params.horizon })
        })
        const data = await res.json()
        
        response = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.error || data.interpretation || 'Forecast generated.',
          forecast: data.forecast
        }
      } else if (intent.type === 'transform') {
        const res = await fetch('/api/transform', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        })
        const data = await res.json()
        
        response = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Transform pipeline triggered.\n\nJob ID: ${data.run_id}\nStatus: ${data.status}\n\nThis typically takes 3-5 minutes.`
        }
      } else {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: input, filters: Object.keys(activeFilters).length > 0 ? activeFilters : null })
        })
        const data = await res.json()
        
        response = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response
        }
      }

      setMessages(prev => [...prev, response])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const quickActions = [
    { label: 'Trending up', query: 'Show me products trending up' },
    { label: 'Trending down', query: 'Show me products trending down' },
    { label: 'Spikes', query: 'Find products with spikes' },
    { label: 'Volatile', query: 'What products are volatile?' },
  ]

  return (
    <div className="flex flex-col h-screen bg-white">
      <header className="border-b px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">PRISM AI</h1>
            <p className="text-sm text-gray-500">Sales Pattern Intelligence</p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-2xl rounded-2xl px-5 py-4 ${
                msg.role === 'user' 
                  ? 'bg-indigo-600 text-white' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                
                {msg.forecast && (
                  <div className="mt-4">
                    <ForecastChart data={msg.forecast} />
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-5 py-4">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t bg-white">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex gap-2 flex-wrap justify-center mb-4">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => setInput(action.query)}
                className="text-sm px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="flex gap-3 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { 
                  if (e.key === 'Enter' && !e.shiftKey) { 
                    e.preventDefault()
                    handleSubmit(e)
                  } 
                }}
                placeholder="Ask about sales patterns, trends, or forecasts..."
                rows={1}
                className="flex-1 px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none text-base"
                style={{ minHeight: '48px', maxHeight: '200px' }}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="p-3 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}