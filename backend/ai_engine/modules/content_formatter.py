"""
Helper to distribute images evenly through article HTML content.
"""
import re


def distribute_images_in_content(content, image_urls):
    """
    Distributes images evenly throughout the article content between paragraphs.
    
    Args:
        content: HTML article content
        image_urls: List of image URLs to insert
        
    Returns:
        Modified HTML content with images distributed evenly
    """
    if not image_urls or not content:
        return content
    
    # Find all closing </p> tags as insertion points
    paragraphs = re.split(r'(</p>)', content)
    
    # Count actual paragraphs (exclude headers and empty strings)
    paragraph_count = sum(1 for p in paragraphs if '</p>' in p)
    
    if paragraph_count < 2:
        # Not enough paragraphs, just append images at the end
        image_html = '\n'.join([
            f'<img src="{url}" alt="Article image" class="img-fluid rounded my-4 w-100" style="max-width: 800px; margin: 20px auto; display: block;" />'
            for url in image_urls
        ])
        return content + '\n' + image_html
    
    # Calculate where to insert images
    # We want to distribute them evenly through the content
    num_images = len(image_urls)
    
    # If only 1 image, put it after 1/3 of content
    # If 2 images, put at 1/3 and 2/3
    # If 3+ images, distribute evenly
    
    insertion_points = []
    for i in range(num_images):
        # Calculate position as fraction of content
        position = (i + 1) / (num_images + 1)
        # Convert to paragraph index
        para_index = int(paragraph_count * position)
        insertion_points.append(para_index)
    
    # Reconstruct content with images inserted
    result = []
    para_counter = 0
    image_counter = 0
    
    for i, segment in enumerate(paragraphs):
        result.append(segment)
        
        # Check if this is a closing </p> tag
        if '</p>' in segment:
            para_counter += 1
            
            # Check if we should insert an image after this paragraph
            if image_counter < len(insertion_points) and para_counter == insertion_points[image_counter]:
                img_url = image_urls[image_counter]
                img_html = f'\n<img src="{img_url}" alt="Article image {image_counter + 1}" class="img-fluid rounded my-4 w-100" style="max-width: 800px; margin: 20px auto; display: block;" />\n'
                result.append(img_html)
                image_counter += 1
    
    return ''.join(result)
