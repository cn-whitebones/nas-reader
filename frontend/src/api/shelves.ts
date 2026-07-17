import http from './http'
import type { BookBrief, Page } from './books'

export interface Shelf {
  id: string
  name: string
  sort_order: number
  book_count: number
  created_at: string
}

// 单书架模式:每个用户仅有一个默认书架
export const shelvesApi = {
  my: () => http.get<Shelf>('/shelves/my'),
  myBooks: () => http.get<BookBrief[]>('/shelves/my/books'),
  // 分页/搜索/排序都走 /books?shelf=my,复用书库同一套后端能力
  myBooksPaged: (params: Record<string, unknown>) =>
    http.get<Page<BookBrief>>('/books', { params: { ...params, shelf: 'my' } }),
  addBook: (book_id: string) => http.post('/shelves/my/books', { book_id }),
  removeBook: (book_id: string) => http.delete(`/shelves/my/books/${book_id}`),
}
