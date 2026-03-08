'use client'

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

interface ForecastData {
  dates: string[]
  values: number[]
  lower_bound: number[]
  upper_bound: number[]
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1c1c1e', border: '1px solid #3a3a3c',
      borderRadius: 8, padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ color: '#8e8e93', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any) => p.name === 'forecast' && (
        <div key={p.name} style={{ color: '#e5e5ea', fontWeight: 600 }}>
          {Number(p.value).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
      ))}
      {payload[0] && (
        <div style={{ color: '#636366', fontSize: 11, marginTop: 2 }}>
          ± {((payload[0].payload.upper - payload[0].payload.lower) / 2)
            .toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
      )}
    </div>
  )
}

export default function ForecastChart({ data }: { data: ForecastData }) {
  if (!data?.values?.length) return (
    <div style={{ color: '#636366', fontSize: 13, padding: '12px 0' }}>
      No forecast data available
    </div>
  )

  const chartData = data.dates.map((date, i) => ({
    date: date.slice(0, 7),
    forecast: Math.round(data.values[i]),
    upper: Math.round(data.upper_bound[i]),
    lower: Math.round(data.lower_bound[i]),
    band: [Math.round(data.lower_bound[i]), Math.round(data.upper_bound[i])],
  }))

  const allVals = [...data.values, ...data.upper_bound, ...data.lower_bound]
  const minY = Math.floor(Math.min(...allVals) * 0.95)
  const maxY = Math.ceil(Math.max(...allVals) * 1.05)

  const tickFormatter = (v: number) =>
    v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`

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
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ color: '#e5e5ea', fontWeight: 500 }}>Sales Forecast</span>
        <span style={{ fontSize: 11 }}>
          {data.dates[0]?.slice(0, 7)} → {data.dates[data.dates.length - 1]?.slice(0, 7)}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#636366" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#636366" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#48484a" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#48484a" stopOpacity={0.1} />
            </linearGradient>
          </defs>

          <CartesianGrid stroke="#2c2c2e" strokeDasharray="4 4" vertical={false} />

          <XAxis
            dataKey="date"
            tick={{ fill: '#636366', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[minY, maxY]}
            tick={{ fill: '#636366', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={tickFormatter}
            width={36}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Confidence band */}
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#bandGrad)"
            fillOpacity={1}
            legendType="none"
            name="upper"
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="#1c1c1e"
            fillOpacity={1}
            legendType="none"
            name="lower"
          />

          {/* Forecast line */}
          <Area
            type="monotone"
            dataKey="forecast"
            stroke="#aeaeb2"
            strokeWidth={2}
            fill="url(#forecastGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#e5e5ea', stroke: '#1c1c1e', strokeWidth: 2 }}
            name="forecast"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Summary row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 8,
        marginTop: 14,
        paddingTop: 12,
        borderTop: '1px solid #2c2c2e',
      }}>
        {[
          { label: 'First', val: data.values[0], date: data.dates[0]?.slice(0, 7) },
          { label: 'Peak', val: Math.max(...data.values), date: data.dates[data.values.indexOf(Math.max(...data.values))]?.slice(0, 7) },
          { label: 'Last', val: data.values[data.values.length - 1], date: data.dates[data.dates.length - 1]?.slice(0, 7) },
        ].map(({ label, val, date }) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#636366', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#e5e5ea' }}>
              {val?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
            <div style={{ fontSize: 10, color: '#48484a', marginTop: 1 }}>{date}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
