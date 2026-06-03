import React, { useState, useEffect } from 'react'

const API_BASE = '/api'

const SOLVER_COLORS = {
  backtracking: { bg: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400', bar: '#3b82f6' },
  informed: { bg: 'bg-green-500', text: 'text-green-600 dark:text-green-400', bar: '#10b981' },
  local_search: { bg: 'bg-orange-500', text: 'text-orange-600 dark:text-orange-400', bar: '#f59e0b' },
  forward_checking: { bg: 'bg-purple-500', text: 'text-purple-600 dark:text-purple-400', bar: '#8b5cf6' },
}

export default function Stats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedMetric, setSelectedMetric] = useState('mean_time_ms')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (!res.ok) throw new Error('Failed to fetch stats')
      const data = await res.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const metrics = [
    { key: 'mean_time_ms', label: 'Avg Time (ms)' },
    { key: 'mean_states', label: 'Avg States' },
    { key: 'mean_backtracks', label: 'Avg Backtracks' },
    { key: 'solve_rate', label: 'Solve Rate' },
  ]

  const getMaxValue = (difficulty) => {
    if (!difficulty.algorithms.length) return 1
    return Math.max(...difficulty.algorithms.map(a => a[selectedMetric] || 0), 1)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <span className="spinner"></span>
          <p className="mt-3 text-gray-600 dark:text-gray-400">Loading statistics...</p>
        </div>
      </div>
    )
  }

  const hasData = stats && stats.difficulties.some(d => d.puzzle_count > 0)

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
        Performance Statistics
      </h1>

      {!hasData ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-12 text-center border border-gray-200 dark:border-gray-700">
          <div className="text-4xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Data Yet
          </h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            Solve some puzzles on the Generate & Solve page to start collecting performance data. 
            Statistics will appear here automatically.
          </p>
        </div>
      ) : (
        <>
          {/* Metric selector */}
          <div className="mb-6 flex flex-wrap gap-2">
            {metrics.map(m => (
              <button
                key={m.key}
                onClick={() => setSelectedMetric(m.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedMetric === m.key
                    ? 'bg-primary-600 text-white shadow-md'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:border-primary-400'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Legend */}
          <div className="mb-6 flex flex-wrap gap-4">
            {Object.entries(SOLVER_COLORS).map(([solver, colors]) => (
              <div key={solver} className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${colors.bg}`}></div>
                <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                  {solver.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>

          {/* Charts by difficulty */}
          <div className="grid md:grid-cols-2 gap-6">
            {stats.difficulties
              .filter(d => d.puzzle_count > 0)
              .map(difficulty => {
                const maxVal = getMaxValue(difficulty)
                return (
                  <div
                    key={difficulty.difficulty}
                    className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                        {difficulty.difficulty}
                      </h3>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {difficulty.puzzle_count} puzzles
                      </span>
                    </div>

                    {/* Bar chart */}
                    <div className="space-y-3">
                      {difficulty.algorithms.map(algo => {
                        const value = algo[selectedMetric] || 0
                        const percentage = maxVal > 0 ? (value / maxVal) * 100 : 0
                        const colors = SOLVER_COLORS[algo.solver] || { bg: 'bg-gray-500', text: 'text-gray-600' }

                        return (
                          <div key={algo.solver}>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">
                                {algo.solver.replace('_', ' ')}
                              </span>
                              <span className={`text-xs font-semibold ${colors.text}`}>
                                {selectedMetric === 'solve_rate'
                                  ? `${(value * 100).toFixed(1)}%`
                                  : typeof value === 'number' && value % 1 !== 0
                                    ? value.toFixed(2)
                                    : value.toLocaleString()}
                              </span>
                            </div>
                            <div className="w-full h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${colors.bg} rounded-full transition-all duration-500`}
                                style={{ width: `${Math.max(percentage, 2)}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Raw data table */}
          <div className="mt-8">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Detailed Statistics
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden">
                <thead>
                  <tr className="bg-gray-100 dark:bg-gray-700">
                    <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Difficulty</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Solver</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Avg Time</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Min/Max Time</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Avg States</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Solve Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.difficulties
                    .filter(d => d.puzzle_count > 0)
                    .flatMap(d =>
                      d.algorithms.map((algo, idx) => (
                        <tr key={`${d.difficulty}-${algo.solver}`} className="border-t border-gray-200 dark:border-gray-700">
                          {idx === 0 && (
                            <td
                              rowSpan={d.algorithms.length}
                              className="px-4 py-2 font-medium text-gray-900 dark:text-gray-100 capitalize align-top"
                            >
                              {d.difficulty}
                            </td>
                          )}
                          <td className="px-4 py-2 capitalize text-gray-700 dark:text-gray-300">
                            {algo.solver.replace('_', ' ')}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">
                            {algo.mean_time_ms.toFixed(1)}ms
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">
                            {algo.min_time_ms}/{algo.max_time_ms}ms
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">
                            {algo.mean_states.toFixed(0)}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-700 dark:text-gray-300">
                            {(algo.solve_rate * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))
                    )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Refresh button */}
          <div className="mt-6 text-center">
            <button
              onClick={fetchStats}
              className="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              🔄 Refresh Stats
            </button>
          </div>
        </>
      )}
    </div>
  )
}
