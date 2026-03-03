# Separating News Articles from Car Catalog

Right now, if an article mentions "Tesla", the AI creates a `CarSpecification` with `make="Tesla"`. This links the article to the Tesla brand page in the Catalog, even if it's just general news (like a banned steering wheel) rather than a specific car model review.

## Proposed Solution: The "News Only" Flag
I suggest we add a simple toggle to the article system: `is_news_only`.

### How it will work:
1. **Backend Model (`Article`)**: We add a boolean flag `is_news_only = models.BooleanField(default=False)`.
2. **Admin Panel**: On the Article edit page, you can check this box. 
3. **Catalog Filtering (`public_views.py`)**: The brand pages (`/cars/brands/{slug}/`) and the model pages will filter out any article where `is_news_only=True`. They won't count toward the `article_count` or show up in the "Related Articles" on the car specs page.
4. **ML Model Awareness**: The ML model can be updated to ignore (or weigh differently) articles marked as `is_news_only` so it learns that these aren't car reviews.
5. **Auto-Tagging**: You can use the `/admin/articles/` "Move" or "Bulk Edit" action to quickly mark articles as "News Only".

## ML Model Check
You also asked me to check the ML model. The ML model (`ai_engine/modules/content_recommender.py`) is currently using TF-IDF. This means it relies heavily on the exact words used in the article. If the article says "Tesla Model S steering wheel", the ML model *will* think it's highly related to the Tesla Model S. 

Adding the `is_news_only` flag is the exact right approach here, because it allows human oversight to override the ML when the content is conceptually different (news vs. car specs) even if the keywords match exactly.

Let me know if this plan sounds good, and I'll implement the `is_news_only` flag!
