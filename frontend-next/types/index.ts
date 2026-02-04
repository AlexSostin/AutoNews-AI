// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Article types
export interface Article {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content: string;
  image: string | null;
  thumbnail_url: string | null;
  image_2: string | null;
  image_2_url: string | null;
  image_3: string | null;
  image_3_url: string | null;
  youtube_url: string | null;
  price_usd: number | null;
  category: number;
  category_name: string;
  category_slug: string;
  tags: number[];
  tag_names: string[];
  author?: string;
  author_name?: string;
  author_channel_url?: string;
  views?: number;
  average_rating: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
  is_published: boolean;
  is_favorited: boolean;
  seo_title: string;
  seo_description: string;
  specs: CarSpecification | null;
  gallery: ArticleImage[];
  comments: Comment[];
}

export interface CarSpecification {
  id: number;
  make?: string;
  model?: string;
  year?: string;
  model_name: string;
  engine: string;
  horsepower: string;
  torque: string;
  zero_to_sixty: string;
  top_speed: string;
  transmission?: string;
  fuel_type?: string;
  price: string;
  release_date: string;
}

export interface ArticleImage {
  id: number;
  image: string;
  image_url: string;
  caption: string;
  order: number;
  created_at: string;
}

// Category & Tag types
export interface Category {
  id: number;
  name: string;
  slug: string;
  article_count: number;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  article_count: number;
}

// Comment types
export interface Comment {
  id: number;
  article: number;
  author_name: string;
  author_email: string;
  content: string;
  created_at: string;
  is_approved: boolean;
}

// Rating types
export interface Rating {
  id: number;
  article: number;
  rating: number;
  user_ip: string;
  created_at: string;
}

// Auth types
export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
}

// Form types
export interface ArticleFormData {
  title: string;
  summary: string;
  content: string;
  category: number;
  tags: number[];
  is_published: boolean;
  youtube_url?: string;
  seo_title?: string;
  seo_description?: string;
}

export interface CommentFormData {
  article: number;
  author_name: string;
  author_email: string;
  content: string;
}

export interface CategoryFormData {
  name: string;
  slug?: string;
}

export interface TagFormData {
  name: string;
  slug?: string;
}
