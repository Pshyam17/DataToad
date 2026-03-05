'use client'

import { TrendingUp, TrendingDown, Activity, Zap, Minus } from 'lucide-react'

interface Pattern {
  product_id: string
  detected_pattern: string
  confidence: number
  trend_direction?: string
  peak_month?: number
  avg_sales?: number
}

const icons: Record<string, React.ReactNode> = {
  fixed_seasonality: <Activity className="w-4 h-4" />,
  varying_seasonality: <Activity className="w-4 h-4" />,
  slow_trend: <TrendingUp className="w-4 h-4" />,
  sudden_spike: <Zap className="w-4 h-4" />,
  sudden_dip: <Zap className="w-4 h-4" />,
  stable_flat: <Minus className="w-4 h-4" />,
  high_volatility: <Activity className="w-4 h-4" />,
}

const colors: Record<string, string> = {
  fixed_seasonality: 'bg-blue-100 text-blue-700',
  varying_seasonality: 'bg-purple-100 text-purple-700',
  slow_trend: 'bg-green-100 text-green-700',
  sudden_spike: 'bg-orange-100 text-orange-700',
  sudden_dip: 'bg-red-100 text-red-700',
  stable_flat: 'bg-gray-100 text-gray-700',
  high_volatility: 'bg-yellow-100 text-yellow-700',
}

export default function PatternCard({ pattern }: { pattern: Pattern }) {
  const icon = icons[pattern.detected_pattern] || <Activity className="w-4 h-4" />
  const color = colors[pattern.detected_pattern] || 'bg-gray-100 text-gray-700'
  const label = pattern.detected_pattern.replace(/_/g, ' ')
  
  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
      <div className="flex items-center justify-between">
        <span className="font-medium text-gray-900">{pattern.product_id}</span>
        <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${color}`}>
          {icon}
          {label}
        </span>
      </div>
      
      <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
        <span>Confidence: {(pattern.confidence * 100).toFixed(0)}%</span>
        
        {pattern.trend_direction && (
          <span className="flex items-center gap-1">
            {pattern.trend_direction === 'increasing' 
              ? <TrendingUp className="w-3 h-3 text-green-600" />
              : <TrendingDown className="w-3 h-3 text-red-600" />
            }
            {pattern.trend_direction}
          </span>
        )}
        
        {pattern.peak_month && <span>Peak: Month {pattern.peak_month}</span>}
        {pattern.avg_sales && <span>Avg: {pattern.avg_sales.toFixed(0)} units</span>}
      </div>
    </div>
  )
}
