interface PaginationProps {
  page: number
  pages: number
  total: number
  size: number
  onPageChange: (page: number) => void
}

export default function Pagination({
  page,
  pages,
  total,
  size,
  onPageChange,
}: PaginationProps) {
  if (pages <= 1) return null

  const from = (page - 1) * size + 1
  const to = Math.min(page * size, total)

  const getPageNumbers = () => {
    const nums: (number | '...')[] = []
    if (pages <= 7) {
      for (let i = 1; i <= pages; i++) nums.push(i)
    } else {
      nums.push(1)
      if (page > 3) nums.push('...')
      for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) {
        nums.push(i)
      }
      if (page < pages - 2) nums.push('...')
      nums.push(pages)
    }
    return nums
  }

  return (
    <div className="pagination">
      <button
        className="pagination-btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        ←
      </button>

      {getPageNumbers().map((n, i) =>
        n === '...' ? (
          <span key={`ellipsis-${i}`} className="pagination-info">
            …
          </span>
        ) : (
          <button
            key={n}
            className={`pagination-btn${n === page ? ' active' : ''}`}
            onClick={() => onPageChange(n)}
          >
            {n}
          </button>
        )
      )}

      <button
        className="pagination-btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= pages}
      >
        →
      </button>

      <span className="pagination-info">
        {from}–{to} из {total}
      </span>
    </div>
  )
}
