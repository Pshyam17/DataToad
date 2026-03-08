'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import { Send, Loader2, BarChart3 } from 'lucide-react'
import ForecastChart from './ForecastChart'
import PatternChart from './PatternChart'

interface ForecastData {
  dates: string[]
  values: number[]
  lower_bound: number[]
  upper_bound: number[]
}

interface PatternResult {
  product_id: string
  pattern_type: string
  score?: number
  trend?: number
  volatility?: number
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  forecast?: ForecastData
  patterns?: PatternResult[]
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm DataToad. I can help you analyze sales patterns, detect trends, and forecast future sales.\n\nTry asking:\n• \"Show me products trending up\"\n• \"Find products with spikes\"\n• \"What products are volatile?\"\n• \"Forecast sales for Product_123 for the next 6 months\""
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
          content: data.response,
          patterns: data.patterns
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
    { label: 'Trending up',   query: 'Show me products trending up'    },
    { label: 'Trending down', query: 'Show me products trending down'  },
    { label: 'Spikes',        query: 'Find products with spikes'       },
    { label: 'Volatile',      query: 'What products are volatile?'     },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f2f2f7' }}>

      {/* Header */}
      <header style={{
        background: 'rgba(242,242,247,0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #e5e5ea',
        padding: '12px 24px',
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36, height: 36,
            background: '#3a3a3c',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <BarChart3 size={18} color="#f2f2f7" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#1c1c1e' }}>DataToad</div>
            <div style={{ fontSize: 12, color: '#8e8e93' }}>Sales Pattern Intelligence</div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 16px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {messages.map(msg => (
            <div key={msg.id} style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: '80%',
                background: msg.role === 'user' ? '#3a3a3c' : '#ffffff',
                color: msg.role === 'user' ? '#f2f2f7' : '#1c1c1e',
                borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                padding: '12px 16px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                fontSize: 14,
                lineHeight: 1.6,
              }}>
                <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{msg.content}</p>
                {msg.forecast && (
                  <div style={{ marginTop: 12 }}>
                    <ForecastChart data={msg.forecast} />
                  </div>
                )}
                {msg.patterns && msg.patterns.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <PatternChart patterns={msg.patterns} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{
                background: '#ffffff', borderRadius: '18px 18px 18px 4px',
                padding: '12px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
              }}>
                <Loader2 size={16} color="#8e8e93" style={{ animation: 'spin 1s linear infinite' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div style={{
        background: 'rgba(242,242,247,0.95)',
        backdropFilter: 'blur(12px)',
        borderTop: '1px solid #e5e5ea',
        padding: '12px 16px 20px',
      }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          {/* Quick actions */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10, justifyContent: 'center' }}>
            {quickActions.map(a => (
              <button key={a.label} onClick={() => setInput(a.query)} style={{
                fontSize: 12, padding: '5px 14px',
                background: '#ffffff', color: '#3a3a3c',
                border: '1px solid #e5e5ea', borderRadius: 20,
                cursor: 'pointer', transition: 'all 0.15s',
                fontFamily: 'inherit',
              }}
                onMouseEnter={e => (e.currentTarget.style.background = '#f2f2f7')}
                onMouseLeave={e => (e.currentTarget.style.background = '#ffffff')}
              >
                {a.label}
              </button>
            ))}
          </div>

          {/* Input row */}
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as any) } }}
                placeholder="Ask about sales patterns, trends, or forecasts..."
                rows={1}
                style={{
                  flex: 1, padding: '12px 16px',
                  background: '#ffffff',
                  border: '1px solid #e5e5ea',
                  borderRadius: 22, resize: 'none',
                  fontSize: 14, color: '#1c1c1e',
                  fontFamily: 'inherit',
                  outline: 'none',
                  minHeight: 48, maxHeight: 200,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                }}
              />
              <button type="submit" disabled={isLoading || !input.trim()} style={{
                width: 44, height: 44,
                background: input.trim() && !isLoading ? '#3a3a3c' : '#e5e5ea',
                border: 'none', borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
                transition: 'background 0.2s', flexShrink: 0,
              }}>
                <Send size={16} color={input.trim() && !isLoading ? '#f2f2f7' : '#aeaeb2'} />
              </button>
            </div>
          </form>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
