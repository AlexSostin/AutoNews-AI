document.addEventListener('DOMContentLoaded', function() {
    // Add delete buttons to image fields
    const imageFields = document.querySelectorAll('input[type="file"][accept="image/*"]');

    imageFields.forEach(function(field) {
        const fieldContainer = field.closest('.field');

        // Check if delete button already exists
        if (fieldContainer && !fieldContainer.querySelector('.delete-image-btn')) {
            // Check if there's an existing image
            const existingImage = fieldContainer.querySelector('a[href*="/media/"]');
            const clearCheckbox = fieldContainer.querySelector('.clear_checkbox input[type="checkbox"]');

            if (existingImage || clearCheckbox) {
                // Create delete button
                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.className = 'delete-image-btn';
                deleteBtn.textContent = '🗑️ Delete';
                deleteBtn.title = 'Delete this image';

                deleteBtn.addEventListener('click', function(e) {
                    e.preventDefault();

                    if (confirm('Are you sure you want to delete this image?')) {
                        // Clear the file input
                        field.value = '';

                        // Check the clear checkbox if it exists
                        if (clearCheckbox) {
                            clearCheckbox.checked = true;
                        }

                        // Remove any existing image preview
                        const img = fieldContainer.querySelector('img');
                        if (img) {
                            img.style.opacity = '0.5';
                            img.style.filter = 'grayscale(100%)';
                        }

                        // Hide the delete button
                        deleteBtn.style.display = 'none';

                        // Show success message
                        showMessage('Image will be deleted when you save the article.', 'info');
                    }
                });

                // Add button after the field
                if (field.nextSibling) {
                    field.parentNode.insertBefore(deleteBtn, field.nextSibling);
                } else {
                    field.parentNode.appendChild(deleteBtn);
                }
            }
        }
    });

    // Function to show temporary messages
    function showMessage(message, type) {
        // Remove existing messages
        const existingMessages = document.querySelectorAll('.custom-admin-message');
        existingMessages.forEach(msg => msg.remove());

        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = `custom-admin-message ${type}`;
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'info' ? '#17a2b8' : '#28a745'};
            color: white;
            padding: 10px 15px;
            border-radius: 4px;
            z-index: 10000;
            font-weight: bold;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;

        document.body.appendChild(messageEl);

        // Remove after 3 seconds
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 3000);
    }
});