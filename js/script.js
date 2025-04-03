// js/script.js

/**
 * Fetches news data, sorts it, takes the latest items, and displays them.
 * Constructs image URLs relative to /images/ if not a full URL.
 * Includes referrer URL in the article link.
 * @param {number} [count=3] - The number of latest news items to display.
 * @param {string} [containerId='latest-news-grid'] - The ID of the container element for the news grid.
 * @param {string} [loadingId='latest-news-loading'] - The ID of the loading message element.
 */
async function loadLatestNews(count = 3, containerId = 'latest-news-grid', loadingId = 'latest-news-loading') {
    const newsContainer = document.getElementById(containerId);
    const loadingMessage = document.getElementById(loadingId);

    // Exit if the target container element doesn't exist on the current page
    if (!newsContainer) {
        // console.log(`DEBUG: News container #${containerId} not found. Skipping latest news load.`);
        return;
    }

    // *** IMPORTANT: Ensure this path correctly points to your JSON file ***
    const newsDataUrl = '/html/nieuws/nieuws-data.json'; // Assuming JSON is in /nieuws/ folder at root

    try {
        const response = await fetch(newsDataUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} fetching ${newsDataUrl}`);
        }
        const newsData = await response.json();

        // Ensure data is sorted by date descending
        newsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        const latestNews = newsData.slice(0, count);

        if (loadingMessage) loadingMessage.remove(); // Remove loading message
        newsContainer.innerHTML = ''; // Clear container

        if (latestNews.length === 0) {
            newsContainer.innerHTML = '<p style="grid-column: 1 / -1; text-align: center;">Geen nieuwsberichten gevonden.</p>';
            return;
        }

        const referrerPath = window.location.pathname; // Get current page path for backlink

        latestNews.forEach(item => {
            const itemDate = new Date(item.date);
            const formattedDate = itemDate.toLocaleDateString('nl-BE', {
                day: 'numeric', month: 'long', year: 'numeric'
            });

            // Construct image URL, assuming images are in /images/nieuws/ unless full URL
            let finalImageUrl = '/images/nieuws/placeholder-news.png'; // Default placeholder
            if (item.image) {
                if (!item.image.startsWith('http://') && !item.image.startsWith('https://')) {
                    // Assume relative path, prepend the base image path
                    finalImageUrl = `/images/nieuws/${item.image.trim()}`;
                } else {
                    // Use the full URL provided
                    finalImageUrl = item.image.trim();
                }
            }

            const summaryText = item.summary || ''; // Use summary if available
            // Construct link to the full article page, passing ID and referrer
            const itemLink = `/html/nieuws/artikel.html?id=${item.id || ''}&ref=${encodeURIComponent(referrerPath)}`;

            // Generate HTML differently based on whether there's a summary
            let articleHtml;
            if (summaryText) {
                articleHtml = `
                <article class="news-item" id="latest-${item.id || ''}">
                    <img src="${finalImageUrl}" alt="${item.title}" loading="lazy">
                    <div class="news-content">
                        <h3><a href="${itemLink}">${item.title}</a></h3>
                        <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                        <p>${summaryText}</p>
                        <a href="${itemLink}" class="read-more">Lees meer »</a>
                    </div>
                </article>
                `;
            } else {
                 articleHtml = `
                 <article class="news-item" id="latest-${item.id || ''}">
                     <img src="${finalImageUrl}" alt="${item.title}" loading="lazy">
                     <div class="news-content">
                         <h3><a href="${itemLink}">${item.title}</a></h3>
                         <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                         <a href="${itemLink}" class="read-more">Lees meer »</a>
                     </div>
                 </article>
             `;
            }

            newsContainer.insertAdjacentHTML('beforeend', articleHtml);
        });

    } catch (error) {
        console.error('Error loading or processing latest news data:', error);
        const displayError = `<p style="color:red; text-align:center; grid-column: 1 / -1;">Kon laatste nieuws niet laden. (${error.message})</p>`;
        if(loadingMessage) {
            loadingMessage.innerHTML = displayError; // Show error in loading message spot
        } else if(newsContainer) {
             newsContainer.innerHTML = displayError; // Show error in news container
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    // --- Page Info ---
    const currentPagePath = window.location.pathname;

    // --- Function Definitions within DOMContentLoaded Scope ---

    /**
     * Fetches HTML from a URL and REPLACES a placeholder element with the fetched content's main element.
     * @param {string} placeholderId - The ID of the element to replace.
     * @param {string} url - The URL to fetch the HTML from (root-relative assumed).
     * @returns {Promise<Element|null>} A promise that resolves with the newly added element or null on failure.
     */
    const loadAndReplace = async (placeholderId, url) => {
        const placeholder = document.getElementById(placeholderId);
        if (!placeholder) {
            // console.warn(`Placeholder element #${placeholderId} not found.`);
            return null;
        }
        if (!placeholder.parentNode) {
            console.error(`Placeholder #${placeholderId} has no parent node, cannot replace.`);
            return null;
        }

        const rootRelativeUrl = url.startsWith('/') ? url : '/' + url;

        try {
            const response = await fetch(rootRelativeUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} for ${rootRelativeUrl}`);
            }
            const html = await response.text();
            const tempContainer = document.createElement('div');
            tempContainer.innerHTML = html.trim();

            // Adjust this selector if _header.html/_footer.html have extra wrappers
            const actualElement = tempContainer.firstChild;

            if (actualElement && actualElement.nodeType === Node.ELEMENT_NODE) {
                placeholder.parentNode.replaceChild(actualElement, placeholder);
                console.log(`Successfully replaced #${placeholderId} with content from ${url}`);
                return actualElement;
            } else {
                console.error(`Could not find a valid element node in fetched HTML for ${url}. Found:`, actualElement);
                placeholder.innerHTML = `<p style="color: red;">Error: Invalid content loaded from ${url}.</p>`;
                return null;
            }
        } catch (error) {
            console.error(`Could not load and replace HTML from ${rootRelativeUrl}:`, error);
            placeholder.innerHTML = `<p style="color: red; text-align: center;">Error loading content from ${url}.</p>`;
            return null;
        }
    };


    /**
     * Initializes Header Functionality (Mobile Toggle, Accordion, Active Links)
     */
    const initializeHeader = () => {
        const menuToggle = document.querySelector('.menu-toggle');
        const mainNavUl = document.querySelector('.main-nav > ul');

        if (!mainNavUl) {
            console.warn("initializeHeader: .main-nav > ul not found. Cannot initialize header.");
            return;
        }

        const mobileBreakpoint = 768; // Match your CSS breakpoint

        // --- Mobile Menu Toggle Logic ---
        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                const isActive = mainNavUl.classList.toggle('active');
                menuToggle.innerHTML = isActive ? '✕' : '☰';
                menuToggle.setAttribute('aria-expanded', isActive);

                // Reset open submenus when main menu closes
                if (!isActive) {
                    mainNavUl.querySelectorAll('li.submenu-open').forEach(li => {
                        li.classList.remove('submenu-open');
                        const sub = li.querySelector(':scope > ul.submenu');
                        if (sub) sub.classList.remove('submenu-active');
                        const parentLink = li.querySelector(':scope > a');
                        if (parentLink) parentLink.setAttribute('aria-expanded', 'false');
                    });
                }
            });
        }

        // --- Mobile Accordion & Desktop Hover Setup ---
        const menuItems = mainNavUl.querySelectorAll(':scope > li');

        menuItems.forEach(li => {
            const parentLink = li.querySelector(':scope > a');
            const submenu = li.querySelector(':scope > ul.submenu');

            if (parentLink && submenu) {
                 parentLink.setAttribute('aria-haspopup', 'true');
                 parentLink.setAttribute('aria-expanded', 'false');

                // Click listener handles mobile accordion
                parentLink.addEventListener('click', (event) => {
                    const isMobileView = window.innerWidth <= mobileBreakpoint && menuToggle && window.getComputedStyle(menuToggle).display !== 'none';

                    if (isMobileView) {
                        // Prevent default link behavior only on mobile if it's a real link
                        if(parentLink.getAttribute('href') && parentLink.getAttribute('href') !== '#') {
                             event.preventDefault();
                        }

                        const isOpening = !li.classList.contains('submenu-open');

                        // Close siblings at the same level
                         if (isOpening) {
                             li.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherLi => {
                                 if (otherLi !== li) {
                                     otherLi.classList.remove('submenu-open');
                                     const otherSubmenu = otherLi.querySelector(':scope > ul.submenu');
                                     if (otherSubmenu) otherSubmenu.classList.remove('submenu-active');
                                     const otherLink = otherLi.querySelector(':scope > a');
                                     if(otherLink) otherLink.setAttribute('aria-expanded', 'false');
                                 }
                             });
                         }

                        // Toggle current item
                        li.classList.toggle('submenu-open', isOpening);
                        submenu.classList.toggle('submenu-active', isOpening); // Ensure submenu display class is toggled
                        parentLink.setAttribute('aria-expanded', isOpening);

                    } // end if(isMobileView)
                }); // end parentLink click listener

                 // --- Handle Nested Submenus (Accordion style on mobile) ---
                 const nestedSubmenuItems = submenu.querySelectorAll(':scope > li');
                 nestedSubmenuItems.forEach(nestedLi => {
                     const nestedParentLink = nestedLi.querySelector(':scope > a');
                     const nestedSubmenu = nestedLi.querySelector(':scope > ul.submenu');

                     if (nestedParentLink && nestedSubmenu) {
                         nestedParentLink.setAttribute('aria-haspopup', 'true');
                         nestedParentLink.setAttribute('aria-expanded', 'false');

                         nestedParentLink.addEventListener('click', (event) => {
                             const isMobileView = window.innerWidth <= mobileBreakpoint && menuToggle && window.getComputedStyle(menuToggle).display !== 'none';
                             if (isMobileView) {
                                  if(nestedParentLink.getAttribute('href') && nestedParentLink.getAttribute('href') !== '#') {
                                      event.preventDefault();
                                 }
                                 const isNestedOpening = !nestedLi.classList.contains('submenu-open');

                                 // Close siblings
                                 if (isNestedOpening) {
                                    nestedLi.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherNestedLi => {
                                        if(otherNestedLi !== nestedLi) {
                                            otherNestedLi.classList.remove('submenu-open');
                                            const otherNestedSub = otherNestedLi.querySelector(':scope > ul.submenu');
                                            if(otherNestedSub) otherNestedSub.classList.remove('submenu-active');
                                            const otherNestedLink = otherNestedLi.querySelector(':scope > a');
                                            if(otherNestedLink) otherNestedLink.setAttribute('aria-expanded', 'false');
                                        }
                                    });
                                 }

                                 // Toggle current
                                 nestedLi.classList.toggle('submenu-open', isNestedOpening);
                                 nestedSubmenu.classList.toggle('submenu-active', isNestedOpening); // Toggle display class
                                 nestedParentLink.setAttribute('aria-expanded', isNestedOpening);
                             } // end if(isMobileView)
                         }); // end nestedParentLink click listener
                     } // end if (nestedParentLink && nestedSubmenu)
                 }); // end nestedSubmenuItems.forEach
            } // End if (parentLink && submenu)
        }); // End menuItems.forEach

        // --- Active Page Link Highlighting Logic ---
        const navLinks = mainNavUl.querySelectorAll('a[href]');

        const normalizePath = (path) => {
            if (!path) return '/';
             try { path = decodeURIComponent(path); } catch (e) { console.warn("Decode path failed:", path, e); }
            if (path.endsWith('/index.html')) path = path.substring(0, path.length - 'index.html'.length);
            if (path.endsWith('/home.html')) path = path.substring(0, path.length - 'home.html'.length);
            if (path.endsWith('.html')) path = path.substring(0, path.length - '.html'.length);
            if (path !== '/' && path.endsWith('/')) path = path.substring(0, path.length - 1);
            if (path === '') path = '/';
            path = path.toLowerCase();
            return path;
        };

        const normalizedCurrentPath = normalizePath(currentPagePath);

        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (!linkHref || linkHref === '#') return;

            let linkPath;
            try { linkPath = new URL(linkHref, window.location.origin).pathname; }
            catch (e) { console.warn(`Invalid nav URL: ${linkHref}`); return; }

            const normalizedLinkPath = normalizePath(linkPath);

            if (normalizedCurrentPath === normalizedLinkPath) {
                link.classList.add('active');
                let currentElement = link.parentElement;
                while (currentElement && currentElement.closest('.main-nav')) {
                    if (currentElement.tagName === 'LI') {
                        currentElement.classList.add('active-ancestor');
                        const parentTriggerLink = currentElement.querySelector(':scope > a');
                        if (parentTriggerLink && !parentTriggerLink.classList.contains('active')) {
                            parentTriggerLink.classList.add('active');
                        }
                        const parentSubmenu = currentElement.closest('ul.submenu');
                        if (parentSubmenu) {
                            currentElement = parentSubmenu.parentElement;
                        } else { break; }
                    } else { break; }
                }
            }
        });
    }; // End initializeHeader

    /**
     * --- NEW --- Initializes Submenu Positioning (Checks for Overflow)
     */
    function initializeSubmenuPositioning() {
        // Select list items within level 2+ submenus that HAVE further nested submenus
        const nestedSubmenuParents = document.querySelectorAll('.main-nav .submenu > li.menu-item-has-children');

        nestedSubmenuParents.forEach(li => {
            const submenu = li.querySelector(':scope > ul.submenu'); // Get the direct child submenu (Level 3+)

            if (!submenu) return; // Skip if no submenu found

            li.addEventListener('mouseenter', () => {
                // Use setTimeout to allow CSS transition to potentially start making submenu visible
                setTimeout(() => {
                    const parentRect = li.getBoundingClientRect();
                    const submenuRect = submenu.getBoundingClientRect(); // Get submenu size
                    const viewportWidth = window.innerWidth;

                    // Check if submenu is actually rendered (width > 0) before calculating
                    if (submenuRect.width > 0) {
                        const predictedRightEdge = parentRect.right + submenuRect.width;
                        const buffer = 10; // Small buffer from edge

                        // console.log(`DEBUG: Parent right: ${parentRect.right.toFixed(0)}, Submenu width: ${submenuRect.width.toFixed(0)}, Predicted right: ${predictedRightEdge.toFixed(0)}, Viewport width: ${viewportWidth}`);

                        if (predictedRightEdge > (viewportWidth - buffer)) {
                            // console.log("DEBUG: Adding submenu-pull-left");
                            li.classList.add('submenu-pull-left');
                        } else {
                            // console.log("DEBUG: Removing submenu-pull-left");
                            li.classList.remove('submenu-pull-left');
                        }
                    } else {
                        // Submenu might not be rendered yet or has no width, remove class just in case
                        li.classList.remove('submenu-pull-left');
                    }
                }, 50); // 50ms delay
            });

            // Remove class on mouseleave for cleanliness
            li.addEventListener('mouseleave', () => {
                 li.classList.remove('submenu-pull-left');
            });
        });
    } // End initializeSubmenuPositioning


    /**
     * Initializes Footer Functionality (Year)
     */
    const initializeFooter = () => {
         const yearSpan = document.getElementById('current-year');
         if (yearSpan) {
             yearSpan.textContent = new Date().getFullYear();
         }
    };


    /**
     * Orchestrates the loading and initialization.
     */
    const loadAll = async () => {
        const headerPlaceholderId = 'header-placeholder';
        const footerPlaceholderId = 'footer-placeholder';
        const headerPath = '/_header.html'; // Adjust path if needed
        const footerPath = '/_footer.html'; // Adjust path if needed

        // Load Header and Footer Concurrently
        await Promise.all([
            loadAndReplace(headerPlaceholderId, headerPath),
            loadAndReplace(footerPlaceholderId, footerPath)
        ]);

        // Initialize AFTER replacements are done
        if (document.querySelector('.site-header')) {
             initializeHeader();
             initializeSubmenuPositioning(); // << Initialize submenu check AFTER header structure is ready
        } else {
            console.warn("loadAll: .site-header not found after load attempt.");
        }

        if (document.querySelector('.site-footer')) {
             initializeFooter();
        } else {
             console.warn("loadAll: .site-footer not found after load attempt.");
        }

        // Load Latest News (can run independently)
        if (typeof loadLatestNews === 'function') {
           await loadLatestNews();
        }

        console.log("Initial content loading and initialization finished.");
    };

    // --- Start Execution ---
    loadAll();

}); // End DOMContentLoaded