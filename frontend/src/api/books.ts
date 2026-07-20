import http from './http'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface BookBrief {
  id: string
  file_name: string
  dir_path: string
  format: 'txt' | 'epub' | 'pdf' | 'mobi' | 'comic'
  status: 'active' | 'missing'
  chapter_count: number
  word_count: number | null
  file_size: number
  has_cover: boolean
  title: string | null
  authors: string[]
}

export interface Metadata {
  title: string | null
  subtitle: string | null
  authors: string[]
  publisher: string | null
  isbn: string | null
  pub_date: string | null
  description: string | null
  language: string | null
  tags: string[]
  rating: number | null
  source_provider: string | null
  scraped_at?: string | null
}

export interface Progress {
  location: string
  percent: number
  chapter_idx: number
  updated_at?: string
}

export interface BookDetail extends BookBrief {
  source_id: string
  rel_path: string
  file_size: number
  added_at: string
  metadata: Metadata | null
  progress: Progress | null
  double_page: boolean
  start_right: boolean
}

export interface Chapter {
  idx: number
  title: string
  location: string
}

export interface ChapterContent {
  idx: number
  title: string
  location: string
  html: string
}

export interface TreeNode {
  name: string
  path: string
  source_id: string
  book_count: number
  children: TreeNode[]
}

export interface BookComicSettingsUpdate {
  double_page?: boolean
  start_right?: boolean
}

export const booksApi = {
  list: (params: Record<string, unknown>) => http.get<Page<BookBrief>>('/books', { params }),
  tree: (source_id?: string) => http.get<TreeNode[]>('/books/tree', { params: { source_id } }),
  detail: (id: string) => http.get<BookDetail>(`/books/${id}`),
  chapters: (id: string) => http.get<Chapter[]>(`/books/${id}/chapters`),
  content: (id: string, chapter_idx: number) =>
    http.get<ChapterContent>(`/books/${id}/content`, { params: { chapter_idx } }),
  fileUrl: (id: string) => `/api/v1/books/${id}/file`,
  coverUrl: (id: string) => `/api/v1/books/${id}/cover`,
  getProgress: (id: string) => http.get<Progress>(`/books/${id}/progress`),
  putProgress: (id: string, p: Omit<Progress, 'updated_at'>) =>
    http.put<Progress>(`/books/${id}/progress`, p),
  updateComicSettings: (id: string, settings: BookComicSettingsUpdate) =>
    http.put<BookDetail>(`/books/${id}/comic_settings`, settings),
}
