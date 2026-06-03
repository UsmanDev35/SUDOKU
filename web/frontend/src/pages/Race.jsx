import React, { useState } from 'react'
import SudokuGrid from '../components/SudokuGrid'
import MetricsCard from '../components/MetricsCard'

const API_BASE = '/api'
const SOLVERS = ['backtracking', 'informed', 'local_search', 'forward_checking']

export default function Race() {
  const [solverA, setSolverA] = useState('backtracking')
  const [solverB, setSolverB] = useState('informed')
  const [puzzle, setPuzzle] = useState(null)
  const [raceResult, setRaceResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  const generatePuzzle = async () => {
    setGenerating(true)
    setRaceResult(null)
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty: 'medium' }),
      })
      if (!res.ok) throw new Error('Generation failed')
      const data = await res.json()
      setPuzzle(data.puzzle)
    } catch (err) {
      alert('Failed to generate puzzle: ' + err.message)
    } finally {
      setGenerating(false)
    }
  }

  const startRace = async () => {
    if (!puzzle) {
      alert('Generate a puzzle first')
      return
    }
    if (solverA === solverB) {
      alert('Please select two different solvers')
      return
    }
    setLoading(true)
    setRaceResult(null)
    try {
      const res = await fetch(`${API_BASE}/race`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          puzzle,
          solver_a: solverA,
          solver_b: solverB,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Race failed')
      }
      const data = await res.json()
      setRaceResult(data)
    } catch (err) {
      alert('Race failed: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
        Adversarial Race
      </h1>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Setup */}
        <div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Race Setup
            </h2>

            {/* Solver A */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Solver A
              </label>
              <div className="flex flex-wrap gap-2">
                {SOLVERS.map(s => (
                  <button
                    key={s}
                    onClick={() => setSolverA(s)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${
                      solverA === s
                        ? 'bg-blue-600 text-white shadow-md'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Solver B */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Solver B
              </label>
              <div className="flex flex-wrap gap-2">
                {SOLVERS.map(s => (
                  <button
                    key={s}
                    onClick={() => setSolverB(s)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${
                      solverB === s
                        ? 'bg-red-600 text-white shadow-md'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {solverA === solverB && (
              <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded-lg text-sm text-yellow-700 dark:text-yellow-300">
                ⚠️ Please select two different solvers
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={generatePuzzle}
                disabled={generating}
                className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg shadow-md transition-colors flex items-center space-x-2"
              >
                {generating && <span className="spinner"></span>}
                <span>{generating ? 'Generating...' : 'Generate Puzzle'}</span>
              </button>
              <button
                onClick={startRace}
                disabled={loading || !puzzle || solverA === solverB}
                className="px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium rounded-lg shadow-md transition-colors flex items-center space-x-2"
              >
                {loading && <span className="spinner"></span>}
                <span>{loading ? 'Racing...' : '🏁 Start Race'}</span>
              </button>
            </div>
          </div>

          {/* Puzzle preview */}
          {puzzle && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Race Puzzle
              </h3>
              <SudokuGrid puzzle={puzzle} />
            </div>
          )}
        </div>

        {/* Right: Results */}
        <div>
          {raceResult && (
            <div>
              {/* Winner announcement */}
              <div className={`mb-6 p-6 rounded-xl text-center shadow-md ${
                raceResult.winner
                  ? 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-300 dark:border-green-700'
                  : 'bg-gradient-to-br from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30 border border-yellow-300 dark:border-yellow-700'
              }`}>
                <div className="text-3xl mb-2">
                  {raceResult.winner ? '🏆' : '🤝'}
                </div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  {raceResult.winner
                    ? `${raceResult.winner.replace('_', ' ')} wins!`
                    : "It's a tie!"}
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Time difference: {raceResult.time_difference_ms}ms
                </p>
              </div>

              {/* Metrics cards */}
              <div className="space-y-4">
                <MetricsCard
                  title={`Solver A: ${raceResult.solver_a.solver}`}
                  status={raceResult.solver_a.status}
                  metrics={{
                    time_ms: raceResult.solver_a.time_ms,
                    states_explored: raceResult.solver_a.states_explored,
                    backtracks: raceResult.solver_a.backtracks,
                  }}
                  highlight={raceResult.winner === raceResult.solver_a.solver}
                />
                <MetricsCard
                  title={`Solver B: ${raceResult.solver_b.solver}`}
                  status={raceResult.solver_b.status}
                  metrics={{
                    time_ms: raceResult.solver_b.time_ms,
                    states_explored: raceResult.solver_b.states_explored,
                    backtracks: raceResult.solver_b.backtracks,
                  }}
                  highlight={raceResult.winner === raceResult.solver_b.solver}
                />
              </div>
            </div>
          )}

          {!raceResult && (
            <div className="flex items-center justify-center h-64 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
              <p className="text-gray-500 dark:text-gray-400 text-center">
                Generate a puzzle and start a race to see results here
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
