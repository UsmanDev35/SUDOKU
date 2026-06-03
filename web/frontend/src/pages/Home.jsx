import React from 'react'
import { Link } from 'react-router-dom'

const features = [
  {
    to: '/solve',
    title: 'Generate & Solve',
    description: 'Generate puzzles at any difficulty and solve them with 4 different AI algorithms. Compare performance side by side.',
    icon: '🧩',
    color: 'from-blue-500 to-blue-600',
  },
  {
    to: '/race',
    title: 'Adversarial Race',
    description: 'Pit two solvers against each other on the same puzzle. See which algorithm wins in a head-to-head race.',
    icon: '🏁',
    color: 'from-purple-500 to-purple-600',
  },
  {
    to: '/stats',
    title: 'Statistics',
    description: 'View aggregate performance data across difficulty levels. Compare algorithm efficiency with charts.',
    icon: '📊',
    color: 'from-green-500 to-green-600',
  },
]

export default function Home() {
  return (
    <div>
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Sudoku Solver Evaluator
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          An AI-powered platform for generating, solving, and evaluating Sudoku puzzles 
          using multiple search algorithms. Compare Backtracking, Informed Search, 
          Local Search, and Forward Checking strategies.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {features.map(feature => (
          <Link
            key={feature.to}
            to={feature.to}
            className="group block"
          >
            <div className="h-full rounded-xl bg-white dark:bg-gray-800 shadow-md hover:shadow-xl transition-all duration-200 border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 p-6 hover:-translate-y-1">
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-lg bg-gradient-to-br ${feature.color} text-white text-2xl mb-4`}>
                {feature.icon}
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                {feature.title}
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-12 text-center">
        <div className="inline-flex items-center space-x-6 text-sm text-gray-500 dark:text-gray-400">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-green-400"></span>
            <span>4 Solvers</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            <span>4 Difficulty Levels</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-purple-400"></span>
            <span>Adversarial Mode</span>
          </span>
        </div>
      </div>
    </div>
  )
}
