import React from 'react'

/**
 * Renders a 9x9 Sudoku grid with styled 3x3 boxes.
 * 
 * Props:
 *  - puzzle: 9x9 array (original puzzle, 0 = empty)
 *  - solution: 9x9 array (solved grid, optional)
 *  - showSolution: boolean to toggle solution display
 */
export default function SudokuGrid({ puzzle, solution = null, showSolution = false }) {
  if (!puzzle || puzzle.length !== 9) return null

  const getBoxIndex = (row, col) => Math.floor(row / 3) * 3 + Math.floor(col / 3)
  const isLightBox = (row, col) => {
    const box = getBoxIndex(row, col)
    return [0, 2, 4, 6, 8].includes(box)
  }

  return (
    <div className="sudoku-grid rounded-lg overflow-hidden shadow-lg">
      {puzzle.map((row, r) =>
        row.map((cellValue, c) => {
          const isFixed = cellValue !== 0
          const displayValue = showSolution && solution
            ? solution[r][c]
            : cellValue || ''
          const isSolved = showSolution && solution && !isFixed && solution[r][c] !== 0

          let classes = 'sudoku-cell'
          if (isFixed) classes += ' fixed'
          if (isSolved) classes += ' solved'
          if (isLightBox(r, c)) classes += ' box-light'
          else classes += ' box-dark'
          if (c % 3 === 2 && c < 8) classes += ' border-right-thick'
          if (r % 3 === 2 && r < 8) classes += ' border-bottom-thick'

          return (
            <div key={`${r}-${c}`} className={classes}>
              {displayValue || ''}
            </div>
          )
        })
      )}
    </div>
  )
}
