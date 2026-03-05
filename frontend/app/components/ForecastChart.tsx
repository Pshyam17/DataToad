'use client'

interface ForecastData {
  dates: string[]
  values: number[]
  lower_bound: number[]
  upper_bound: number[]
}

export default function ForecastChart({ data }: { data: ForecastData }) {
  if (!data || !data.values || data.values.length === 0) {
    return <div className="text-gray-500 text-sm">No forecast data available</div>
  }

  const maxVal = Math.max(...data.upper_bound)
  const minVal = Math.min(...data.lower_bound)
  const range = maxVal - minVal || 1
  
  const getY = (val: number) => 100 - ((val - minVal) / range) * 80 - 10
  
  const points = data.values.map((v, i) => {
    const x = data.values.length > 1 ? (i / (data.values.length - 1)) * 280 + 10 : 150
    return `${x},${getY(v)}`
  }).join(' ')
  
  const upperPoints = data.upper_bound.map((v, i) => {
    const x = data.values.length > 1 ? (i / (data.values.length - 1)) * 280 + 10 : 150
    return `${x},${getY(v)}`
  })
  
  const lowerPoints = data.lower_bound.map((v, i) => {
    const x = data.values.length > 1 ? ((data.values.length - 1 - i) / (data.values.length - 1)) * 280 + 10 : 150
    return `${x},${getY(v)}`
  }).reverse()
  
  const areaPoints = [...upperPoints, ...lowerPoints].join(' ')
  
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="text-sm font-medium text-gray-700 mb-3">Forecast</div>
      
      <svg viewBox="0 0 300 120" className="w-full h-32">
        <polygon points={areaPoints} fill="rgba(99, 102, 241, 0.2)" />
        
        <polyline
          points={points}
          fill="none"
          stroke="#6366f1"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {data.values.map((v, i) => {
          const x = data.values.length > 1 ? (i / (data.values.length - 1)) * 280 + 10 : 150
          return <circle key={i} cx={x} cy={getY(v)} r="4" fill="#6366f1" />
        })}
      </svg>
      
      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>{data.dates[0]}</span>
        <span>{data.dates[data.dates.length - 1]}</span>
      </div>
      
      <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
        {data.values.slice(0, 3).map((v, i) => (
          <div key={i} className="text-center">
            <div className="text-gray-500 text-xs">{data.dates[i]}</div>
            <div className="font-medium">{v.toFixed(0)}</div>
            <div className="text-xs text-gray-400">
              ±{((data.upper_bound[i] - data.lower_bound[i]) / 2).toFixed(0)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}