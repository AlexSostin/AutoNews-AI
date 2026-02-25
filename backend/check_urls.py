import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article

urls = [
    "https://www.youtube.com/watch?v=VK9XyTF7Rno",
    "https://www.youtube.com/watch?v=Tj3bQvsUeLs",
    "https://www.youtube.com/watch?v=rh-e5EHZkP8",
    "https://www.youtube.com/watch?v=QQbw4tCZxFc",
    "https://www.youtube.com/watch?v=PUtQ75IQ0r0",
    "https://www.youtube.com/watch?v=quB_Ygttr-Q",
    "https://www.youtube.com/watch?v=-MswT3H0Wt4",
    "https://www.youtube.com/watch?v=hjYKGtn2ISI",
    "https://www.youtube.com/watch?v=TtQQjRRFaCQ",
    "https://www.youtube.com/watch?v=GW8saw1TSTk",
    "https://www.youtube.com/watch?v=UPOYYgJOf9Y",
    "https://www.youtube.com/watch?v=wcJYViDC6U0",
    "https://www.youtube.com/watch?v=Ui272uy3WWA",
    "https://www.youtube.com/watch?v=LuvqLxgH6M0",
    "https://www.youtube.com/watch?v=o8gHV9uYsMI",
    "https://www.youtube.com/watch?v=RldKysuZpPA",
    "https://www.youtube.com/watch?v=oS1ehPyVDNg",
    "https://www.youtube.com/watch?v=WNBJMErQCCo",
    "https://www.youtube.com/watch?v=Pd_HVP0A5CE",
    "https://www.youtube.com/watch?v=Yo6e5T1BaoE"
]

found_urls = Article.objects.filter(youtube_url__in=urls).values_list('youtube_url', flat=True)
for url in found_urls:
    print(f"FOUND:{url}")
