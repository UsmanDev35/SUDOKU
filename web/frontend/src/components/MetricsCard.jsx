import React from 'react'

/**
 * Displays solver metrics in a card format.
 * 
 * Props:
 *  - title: Card title (solver name)
 *  - status: solve status string
 *  - metrics: { time_ms, states_explored, backtracks }
 *  - highlight: whether to highlight as winner
 */
export default function MetricsCard({ title, status, metrics, highlight = false }) {
  const statusColors = {
    solved: 'text-green-600 dark:text-green-400',
    timeout: 'text-yellow-600 dark:text-yellow-400',
    failed: 'text-red-600 dark:text-red-400',
    unsolvable: 'text-red-600 dark:text-red-400',
  }

  const statusColor = statusColors[status] || 'text-gray-600 dark:text-gray-400'

  return (
    <div className={`rounded-xl p-5 shadow-md transition-all ${
      highlight
        ? 'bg-green-50 dark:bg-green-900/30 border-2 border-green-400 dark:border-green-600'
        : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 capitalize">
          {title.replace('_', ' ')}
        </h3>
        <span className={`text-sm font-medium ${statusColor} capitalize`}>
          {status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
            {metrics.time_ms}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Time (ms)</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
            {metrics.states_explored.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">States</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
            {metrics.backtracks.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Backtracks</div>
        </div>
      </div>

      {highlight && (
        <div className="mt-3 text-center text-sm font-medium text-green-600 dark:text-green-400">
          🏆 Winner
        </div>
      )}
    </div>
  )
}
