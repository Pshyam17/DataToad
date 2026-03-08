'use client'

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

interface PatternResult {
  product_id: string
  pattern_type: string
  score?: number
  trend?: number
  volatility?: number
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1c1c1e', border: '1px solid #3a3a3c',
      borderRadius: 8, padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ color: '#8e8e93', marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#e5e5ea', fontWeight: 600 }}>
        Score: {Number(payload[0]?.value).toFixed(3)}
      </div>
    </div>
  )
}

const MUTED = ['#636366', '#48484a', '#8e8e93', '#aeaeb2', '#5a5a5e']

export default function PatternChart({ patterns }: { patterns: PatternResult[] }) {
  if (!patterns?.length) return null

  const top = patterns.slice(0, 8).map(p => ({
    id: p.product_id?.slice(-8) ?? 'unknown',
    full_id: p.product_id,
    score: +(p.score ?? p.trend ?? p.volatility ?? 0).toFixed(4),
    type: p.pattern_type,
  }))

  return (
    <div style={{
      background: '#1c1c1e',
      border: '1px solid #2c2c2e',
      borderRadius: 12,
      padding: '20px 16px 12px',
      marginTop: 12,
    }}>
      <div style={{
        fontSize: 12, color: '#8e8e93', marginBottom: 16,
        display: 'flex', justifyContent: 'space-between',
      }}>
        <span style={{ color: '#e5e5ea', fontWeight: 500 }}>Pattern Results</span>
        <span>{patterns.length} products matched</span>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={top} margin={{ top: 0, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#2c2c2e" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="id"
            tick={{ fill: '#636366', fontSize: 9 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: '#636366', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="score" radius={[3, 3, 0, 0]} maxBarSize={32}>
            {top.map((_, i) => (
              <Cell key={i} fill={MUTED[i % MUTED.length]} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Product list */}
      <div style={{
        marginTop: 12, paddingTop: 12,
        borderTop: '1px solid #2c2c2e',
        display: 'flex', flexWrap: 'wrap', gap: 6,
      }}>
        {patterns.slice(0, 12).map((p, i) => (
          <span key={i} style={{
            background: '#2c2c2e', color: '#aeaeb2',
            borderRadius: 4, padding: '2px 8px', fontSize: 11,
          }}>
            {p.product_id}
          </span>
        ))}
        {patterns.length > 12 && (
          <span style={{ color: '#636366', fontSize: 11, padding: '2px 4px' }}>
            +{patterns.length - 12} more
          </span>
        )}
      </div>
    </div>
  )
}
