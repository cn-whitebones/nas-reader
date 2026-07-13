import http from './http'
import type { BookBrief } from './books'

export interface Shelf {
  id: string
  name: string
  sort_order: number
  book_count: number
  created_at: string
}

export const shelvesApi = {
  list: () => http.get<Shelf[]>('/shelves'),
  create: (name: string, sort_order = 0) => http.post<Shelf>('/shelves', { name, sort_order }),
  update: (id: string, data: Partial<Pick<Shelf, 'name' | 'sort_order'>>) =>
    http.patch<Shelf>(`/shelves/${id}`, data),
  remove: (id: string) => http.delete(`/shelves/${id}`),
  books: (id: string) => http.get<BookBrief[]>(`/shelves/${id}/books`),
  addBook: (id: string, book_id: string) => http.post(`/shelves/${id}/books`, { book_id }),
  removeBook: (id: string, book_id: string) => http.delete(`/shelves/${id}/books/${book_id}`),
}
