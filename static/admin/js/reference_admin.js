// JavaScript to automatically populate authors_order field based on selection order
console.log('REFERENCE ADMIN JS LOADED - VERSION 2');
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        // Wait for Django's admin to be ready
        if (typeof django === 'undefined' || !django.jQuery) {
            setTimeout(arguments.callee, 100);
            return;
        }
        
        const $ = django.jQuery;
        
        // Debug: Check what elements are available
        console.log('Author ordering: Looking for elements...');
        console.log('Available elements with "authors" in ID:', $('[id*="authors"]').length);
        $('[id*="authors"]').each(function() {
            console.log('Found element:', this.id, this.tagName, this.className);
        });
        
        // Look for the actual authors field (regular select or filter horizontal)
        let authorsField = $('#id_authors');
        let authorsOrderField = $('#id_authors_order');
        
        // Check if it's a filter horizontal widget
        let authorsFrom = $('#id_authors_from');
        let authorsTo = $('#id_authors_to');
        let isFilterHorizontal = authorsFrom.length > 0 && authorsTo.length > 0;
        
        console.log('Filter horizontal widget:', isFilterHorizontal);
        console.log('Regular authors field:', authorsField.length > 0);
        console.log('Authors order field:', authorsOrderField.length > 0);
        
        if (!authorsOrderField.length) {
            console.log('Author ordering: authors_order field not found');
            return;
        }
        
        if (isFilterHorizontal) {
            console.log('Author ordering: Using filter horizontal widget');
            setupFilterHorizontalOrdering();
        } else if (authorsField.length > 0) {
            console.log('Author ordering: Using regular select field');
            setupRegularSelectOrdering();
        } else {
            console.log('Author ordering: No compatible field found');
            return;
        }
        
        function setupFilterHorizontalOrdering() {
            function updateAuthorsOrder() {
                const selectedOptions = authorsTo.find('option');
                const authorIds = selectedOptions.map(function() {
                    return $(this).val();
                }).get();
                
                authorsOrderField.val(authorIds.join(','));
                console.log('Filter horizontal - Author ordering updated:', authorIds.join(','));
            }
            
            // Watch for changes
            authorsTo.on('change', updateAuthorsOrder);
            $('.selector-chooser a').on('click', function() {
                setTimeout(updateAuthorsOrder, 100);
            });
            
            // Add reorder buttons
            addReorderButtons(authorsTo, updateAuthorsOrder);
            
            // Initialize
            updateAuthorsOrder();
        }
        
        function setupRegularSelectOrdering() {
            // For regular select field, we need to track the order manually
            let selectedAuthors = [];
            
            function updateAuthorsOrder() {
                const currentSelected = authorsField.find('option:selected').map(function() {
                    return $(this).val();
                }).get();
                
                // Preserve order by keeping track of selection sequence
                const newOrder = [];
                
                // Add previously selected authors in their original order
                selectedAuthors.forEach(function(authorId) {
                    if (currentSelected.includes(authorId)) {
                        newOrder.push(authorId);
                    }
                });
                
                // Add newly selected authors
                currentSelected.forEach(function(authorId) {
                    if (!selectedAuthors.includes(authorId)) {
                        newOrder.push(authorId);
                    }
                });
                
                selectedAuthors = newOrder;
                authorsOrderField.val(selectedAuthors.join(','));
                console.log('Regular select - Author ordering updated:', selectedAuthors.join(','));
            }
            
            // Watch for changes
            authorsField.on('change', updateAuthorsOrder);
            
            // Add manual reorder interface
            addSelectReorderInterface();
            
            // Initialize
            updateAuthorsOrder();
        }
        
        function addSelectReorderInterface() {
            if ($('.author-reorder-interface').length > 0) return;
            
            const interfaceHtml = `
                <div class="author-reorder-interface" style="margin-top: 10px; padding: 10px; background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;">
                    <strong>Author Order:</strong>
                    <div id="author-order-list" style="margin: 10px 0; min-height: 60px; border: 1px solid #ccc; padding: 10px; background: white;">
                        <em>Select authors from the dropdown above to set their order</em>
                    </div>
                    <button type="button" id="clear-author-order" style="padding: 5px 10px;">Clear Order</button>
                </div>
            `;
            
            authorsField.after(interfaceHtml);
            
            // Update the visual order display
            function updateOrderDisplay() {
                const orderList = $('#author-order-list');
                if (selectedAuthors.length === 0) {
                    orderList.html('<em>No authors selected</em>');
                    return;
                }
                
                let html = '<ol>';
                selectedAuthors.forEach(function(authorId) {
                    const authorName = authorsField.find('option[value="' + authorId + '"]').text();
                    html += '<li>' + authorName + ' <button type="button" class="remove-author" data-author="' + authorId + '" style="margin-left: 10px; padding: 2px 6px; font-size: 11px;">Remove</button></li>';
                });
                html += '</ol>';
                orderList.html(html);
                
                // Add remove functionality
                $('.remove-author').on('click', function() {
                    const authorId = $(this).data('author');
                    selectedAuthors = selectedAuthors.filter(id => id !== authorId);
                    
                    // Unselect from the main field
                    authorsField.find('option[value="' + authorId + '"]').prop('selected', false);
                    
                    updateOrderDisplay();
                    authorsOrderField.val(selectedAuthors.join(','));
                    console.log('Author removed, new order:', selectedAuthors.join(','));
                });
            }
            
            // Clear order button
            $('#clear-author-order').on('click', function() {
                selectedAuthors = [];
                authorsField.find('option').prop('selected', false);
                updateOrderDisplay();
                authorsOrderField.val('');
                console.log('Author order cleared');
            });
            
            // Update display when authors change
            authorsField.on('change', function() {
                setTimeout(updateOrderDisplay, 50);
            });
        }
        
        function addReorderButtons(targetElement, updateFunction) {
            if ($('.author-reorder-buttons').length > 0) return;
            
            const buttonsHtml = `
                <div class="author-reorder-buttons" style="margin-top: 10px; padding: 10px; background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;">
                    <strong>Reorder Authors:</strong><br>
                    <button type="button" id="move-author-up" style="margin-right: 5px; padding: 5px 10px;">↑ Move Up</button>
                    <button type="button" id="move-author-down" style="padding: 5px 10px;">↓ Move Down</button>
                    <p style="font-size: 11px; color: #666; margin: 8px 0 0 0;">
                        Select an author in the "Chosen authors" box and click these buttons to reorder.
                    </p>
                </div>
            `;
            
            targetElement.after(buttonsHtml);
            
            // Move author up
            $('#move-author-up').on('click', function(e) {
                e.preventDefault();
                const selected = targetElement.find('option:selected');
                if (selected.length === 1) {
                    const prev = selected.prev('option');
                    if (prev.length > 0) {
                        selected.insertBefore(prev);
                        updateFunction();
                    }
                }
            });
            
            // Move author down
            $('#move-author-down').on('click', function(e) {
                e.preventDefault();
                const selected = targetElement.find('option:selected');
                if (selected.length === 1) {
                    const next = selected.next('option');
                    if (next.length > 0) {
                        selected.insertAfter(next);
                        updateFunction();
                    }
                }
            });
        }
        
        // Ensure the field is updated before form submission
        $('form').on('submit', function() {
            if (isFilterHorizontal) {
                const selectedOptions = authorsTo.find('option');
                const authorIds = selectedOptions.map(function() {
                    return $(this).val();
                }).get();
                authorsOrderField.val(authorIds.join(','));
            } else {
                authorsOrderField.val(selectedAuthors.join(','));
            }
        });
    });
})(); 