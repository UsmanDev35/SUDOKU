import React, { useState } from 'react'
import SudokuGrid from '../components/SudokuGrid'
import MetricsCard from '../components/MetricsCard'

const API_BASE = '/api'

const DIFFICULTIES = ['easy', 'medium', 'hard', 'expert']
const SOLVERS = ['backtracking', 'informed', 'local_search', 'forward_checking']

export default function GenerateSolve() {
  const [difficulty, setDifficulty] = useState('medium')
  const [puzzle, setPuzzle] = useState(null)
  const [puzzleId, setPuzzleId] = useState(null)
  const [filledCells, setFilledCells] = useState(0)
  const [selectedSolver, setSelectedSolver] = useState('backtracking')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [solving, setSolving] = useState(false)
  const [showSolution, setShowSolution] = useState(false)

  const generatePuzzle = async () => {
    setLoading(true)
    setResults([])
    setShowSolution(false)
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty }),
      })
      if (!res.ok) throw new Error('Generation failed')
      const data = await res.json()
      setPuzzle(data.puzzle)
      setPuzzleId(data.puzzle_id)
      setFilledCells(data.filled_cells)
    } catch (err) {
      alert('Failed to generate puzzle: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const solvePuzzle = async (solver) => {
    if (!puzzle) return
    setSolving(true)
    setShowSolution(false)
    try {
      const res = await fetch(`${API_BASE}/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ puzzle, solver }),
      })
      if (!res.ok) throw new Error('Solve failed')
      const data = await res.json()
      setResults(data.results)
      setShowSolution(true)
    } catch (err) {
      alert('Failed to solve puzzle: ' + err.message)
    } finally {
      setSolving(false)
    }
  }

  const activeSolution = results.length > 0 ? results[0].solution : null

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
        Generate & Solve
      </h1>

      {/* Difficulty Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Difficulty Level
        </label>
        <div className="flex flex-wrap gap-2">
          {DIFFICULTIES.map(d => (
            <button
              key={d}
              onClick={() => setDifficulty(d)}
              className={`px-4 py-2 rounded-lg font-medium text-sm capitalize transition-all ${
                difficulty === d
                  ? 'bg-primary-600 text-white shadow-md'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:border-primary-400'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Generate Button */}
      <button
        onClick={generatePuzzle}
        disabled={loading}
        className="mb-8 px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg shadow-md transition-colors flex items-center space-x-2"
      >
        {loading && <span className="spinner"></span>}
        <span>{loading ? 'Generating...' : 'Generate Puzzle'}</span>
      </button>

      {/* Puzzle Display */}
      {puzzle && (
        <div className="grid lg:grid-cols-2 gap-8">
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {showSolution ? 'Solution' : 'Puzzle'}
              </h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {filledCells} filled cells • {difficulty}
              </span>
            </div>
            <SudokuGrid
              puzzle={puzzle}
              solution={activeSolution}
              showSolution={showSolution}
            />
          </div>

          <div>
            {/* Solver Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Solver
              </label>
              <div className="flex flex-wrap gap-2 mb-4">
                {SOLVERS.map(s => (
                  <button
                    key={s}
                    onClick={() => setSelectedSolver(s)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${
                      selectedSolver === s
                        ? 'bg-purple-600 text-white shadow-md'
                        : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:border-purple-400'
                    }`}
                  >
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => solvePuzzle(selectedSolver)}
                  disabled={solving}
                  className="px-5 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-lg shadow-md transition-colors flex items-center space-x-2"
                >
                  {solving && <span className="spinner"></span>}
                  <span>{solving ? 'Solving...' : 'Solve'}</span>
                </button>
                <button
                  onClick={() => solvePuzzle('all')}
                  disabled={solving}
                  className="px-5 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400 text-white font-medium rounded-lg shadow-md transition-colors flex items-center space-x-2"
                >
                  {solving && <span className="spinner"></span>}
                  <span>{solving ? 'Running...' : 'Run All Solvers'}</span>
                </button>
              </div>
            </div>

            {/* Results */}
            {results.length > 0 && (
              <div className="mt-6 space-y-3">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Results
                </h3>
                {results.map(r => (
                  <MetricsCard
                    key={r.solver}
                    title={r.solver}
                    status={r.status}
                    metrics={{
                      time_ms: r.time_ms,
                      states_explored: r.states_explored,
                      backtracks: r.backtracks,
                    }}
                  />
                ))}
              </div>
            )}

            {/* Comparison Table */}
            {results.length > 1 && (
              <div className="mt-6 overflow-x-auto">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  Comparison Table
                </h3>
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-100 dark:bg-gray-700">
                      <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300 rounded-tl-lg">Solver</th>
                      <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300">Status</th>
                      <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300">Time (ms)</th>
                      <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300">States</th>
                      <th className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300 rounded-tr-lg">Backtracks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results
                      .sort((a, b) => a.time_ms - b.time_ms)
                      .map((r, idx) => (
                        <tr
                          key={r.solver}
                          className={`border-t border-gray-200 dark:border-gray-700 ${
                            idx === 0 && r.status === 'solved' ? 'bg-green-50 dark:bg-green-900/20' : ''
                          }`}
                        >
                          <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100 capitalize">
                            {idx === 0 && r.status === 'solved' && '🏆 '}
                            {r.solver.replace('_', ' ')}
                          </td>
                          <td className="px-3 py-2 capitalize text-gray-700 dark:text-gray-300">{r.status}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{r.time_ms}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{r.states_explored.toLocaleString()}</td>
                          <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{r.backtracks.toLocaleString()}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
