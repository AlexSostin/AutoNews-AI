export interface TagGroup {
    id: number;
    name: string;
    slug: string;
    order: number;
}

export interface Tag {
    id: number;
    name: string;
    slug: string;
    group: number | null;
    group_name: string | null;
    article_count: number;
}
