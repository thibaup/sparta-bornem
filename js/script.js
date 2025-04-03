// js/scripts.js

// --- Global Scope Variables and Functions for Footer Positioning ---
let resizeTimerFooter; // Timer variable for debouncing resize

function adjustFooterPosition() {
    const footerElement = document.querySelector('.site-footer'); // Target the actual footer
    const body = document.body;
    const html = document.documentElement;

    if (!footerElement) {
        // console.warn("adjustFooterPosition: Footer element (.site-footer) not found.");
        return; // Exit if footer isn't in the DOM yet
    }

    // Adding a small delay can sometimes help ensure layout calculations are complete
    setTimeout(() => {
        const totalPageHeight = Math.max( body.scrollHeight, body.offsetHeight,
                               html.clientHeight, html.scrollHeight, html.offsetHeight );
        const viewportHeight = window.innerHeight;

        // console.log(`DEBUG: Page Height: ${totalPageHeight}, Viewport Height: ${viewportHeight}`);
        
        console.log(totalPageHeight, viewportHeight)
        if (totalPageHeight <= viewportHeight) {
            // Page content is short: Stick footer absolutely
            // console.log("DEBUG: Setting footer to absolute");
            footerElement.style.position = 'absolute';
            footerElement.style.left = '0';
            footerElement.style.width = '100%';
            footerElement.style.bottom = '0';
        } else {
            // Page content is long: Revert footer to CSS default (relative)
            // console.log("DEBUG: Reverting footer to CSS default position");
            footerElement.style.position = ''; // Let CSS handle 'relative'
            footerElement.style.left = '';
            footerElement.style.width = '';
            footerElement.style.bottom = '';
        }
    }, 10); // Small delay (10ms) - adjust if necessary

}

/**
 * Debounce function to limit how often adjustFooterPosition runs on resize.
 */
function debounceFooterAdjust() {
    clearTimeout(resizeTimerFooter);
    resizeTimerFooter = setTimeout(adjustFooterPosition, 150); // 150ms delay
}

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

        newsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        const latestNews = newsData.slice(0, count);

        if (loadingMessage) loadingMessage.remove();
        newsContainer.innerHTML = '';

        if (latestNews.length === 0) {
            newsContainer.innerHTML = '<p style="grid-column: 1 / -1; text-align: center;">Geen nieuwsberichten gevonden.</p>';
            return; 
        }

        const referrerPath = window.location.pathname;

        latestNews.forEach(item => {
            const itemDate = new Date(item.date);
            const formattedDate = itemDate.toLocaleDateString('nl-BE', {
                day: 'numeric', month: 'long', year: 'numeric'
            });

            let finalImageUrl = '/images/nieuws/placeholder-news.png'; 
            if (item.image) { 
                if (!item.image.startsWith('http://') && !item.image.startsWith('https://')) {
                    finalImageUrl = `/images/nieuws/${item.image.trim()}`;
                } else {
                    finalImageUrl = item.image.trim();
                }
            }

            const summaryText = item.summary || '';
            const itemLink = `/html/nieuws/artikel.html?id=${item.id || ''}&ref=${encodeURIComponent(referrerPath)}`;

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
            loadingMessage.innerHTML = displayError;
        } else if(newsContainer) {
             newsContainer.innerHTML = displayError;
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const headerPlaceholder = document.getElementById('header-placeholder');
    const footerPlaceholder = document.getElementById('footer-placeholder');

    // --- Page Info ---
    const currentPagePath = window.location.pathname;


    // --- Function Definitions within DOMContentLoaded Scope ---
    const loadHTML = async (url, placeholder) => {
        const rootRelativeUrl = url.startsWith('/') ? url : '/' + url;

        try {
            const response = await fetch(rootRelativeUrl);
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status} for ${rootRelativeUrl}`);
                placeholder.innerHTML = `<p style="color: red; text-align: center;">Error: Could not load ${url}. Check path.</p>`;
                return false;
            }
            const html = await response.text();
            placeholder.innerHTML = html;
            return true;
        } catch (error) {
            console.error(`Could not load HTML from ${rootRelativeUrl}:`, error);
            placeholder.innerHTML = `<p style="color: red; text-align: center;">Error loading content from ${url}.</p>`;
            return false;
        }
    };

    /**
     * Initializes Header Functionality (Mobile Toggle, Accordion, Active Links)
     */
    const initializeHeader = () => {
        const menuToggle = document.querySelector('.menu-toggle');
        const mainNavUl = document.querySelector('.main-nav > ul');
        const mobileBreakpoint = 992;

        // --- Mobile Menu Toggle Logic ---
        if (menuToggle && mainNavUl) {
            menuToggle.addEventListener('click', () => {
                const isActive = mainNavUl.classList.toggle('active'); 
                menuToggle.innerHTML = isActive ? '✕' : '☰'; 
                menuToggle.setAttribute('aria-expanded', isActive);

                // Reset any open submenus when the main menu is closed
                if (!isActive) {
                    mainNavUl.querySelectorAll('li.submenu-open').forEach(li => {
                        li.classList.remove('submenu-open');
                        const sub = li.querySelector(':scope > ul.submenu');
                        if (sub) {
                            sub.classList.remove('submenu-active');
                        }
                        const parentLink = li.querySelector(':scope > a');
                        if (parentLink) {
                            parentLink.setAttribute('aria-expanded', 'false');
                        }
                    });
                }
            });
        } else {
            console.warn("Header initialization warning: Menu toggle button or nav UL not found.");
        }

        const menuItems = mainNavUl.querySelectorAll(':scope > li');

        menuItems.forEach(li => {
            const parentLink = li.querySelector(':scope > a');
            const submenu = li.querySelector(':scope > ul.submenu'); 

            if (parentLink && submenu) {
                 parentLink.setAttribute('aria-haspopup', 'true');
                 parentLink.setAttribute('aria-expanded', 'false');

                parentLink.addEventListener('click', (event) => {
                    const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';

                    if (isMobileView) {
                        if(parentLink.getAttribute('href') && parentLink.getAttribute('href') !== '#') {
                             event.preventDefault();
                        }

                        const isOpening = !li.classList.contains('submenu-open');

                         if (isOpening) {
                             li.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherLi => {
                                 if (otherLi !== li) {
                                     otherLi.classList.remove('submenu-open');
                                     const otherSubmenu = otherLi.querySelector(':scope > ul.submenu');
                                     if (otherSubmenu) otherSubmenu.classList.remove('submenu-active');
                                     const otherLink = otherLi.querySelector(':scope > a');
                                      if(otherLink) {
                                         otherLink.setAttribute('aria-expanded', 'false');
                                      }
                                 }
                             });
                         }

                        // Now toggle the current item
                        li.classList.toggle('submenu-open', isOpening);
                        submenu.classList.toggle('submenu-active', isOpening);
                        parentLink.setAttribute('aria-expanded', isOpening);

                    }
                });

                 const nestedSubmenuItems = submenu.querySelectorAll(':scope > li');
                 nestedSubmenuItems.forEach(nestedLi => {
                     const nestedParentLink = nestedLi.querySelector(':scope > a');
                     const nestedSubmenu = nestedLi.querySelector(':scope > ul.submenu');

                     if (nestedParentLink && nestedSubmenu) {
                         nestedParentLink.setAttribute('aria-haspopup', 'true');
                         nestedParentLink.setAttribute('aria-expanded', 'false');

                         nestedParentLink.addEventListener('click', (event) => {
                             const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';
                             if (isMobileView) {
                                 if(nestedParentLink.getAttribute('href') && nestedParentLink.getAttribute('href') !== '#') {
                                      event.preventDefault();
                                 }
                                 const isNestedOpening = !nestedLi.classList.contains('submenu-open');

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

                                 nestedLi.classList.toggle('submenu-open', isNestedOpening);
                                 nestedSubmenu.classList.toggle('submenu-active', isNestedOpening);
                                 nestedParentLink.setAttribute('aria-expanded', isNestedOpening);
                             }
                         });
                     }
                 });


            } // End if (parentLink && submenu)
        }); // End menuItems.forEach


        // --- Active Page Link Highlighting Logic ---
        const navLinks = mainNavUl.querySelectorAll('a[href]'); // Select all links with href within the main nav UL

        /**
         * Normalizes a URL path for comparison.
         * Removes trailing index/home.html, removes trailing .html,
         * removes trailing slash (unless root), decodes URI components,
         * converts to lowercase.
         * @param {string} path - The URL path to normalize.
         * @returns {string} The normalized path.
         */
        const normalizePath = (path) => {
            if (!path) return '/'; // Handle null/undefined path

             // 1. Decode URI component first (handles spaces %20 etc.)
             try {
                path = decodeURIComponent(path);
            } catch (e) {
                 console.warn("Could not decode path component:", path, e);
                 // Continue with the potentially encoded path if decoding fails
            }

            // 2. Remove index.html or home.html from the end
            if (path.endsWith('/index.html')) {
                path = path.substring(0, path.length - 'index.html'.length);
            } else if (path.endsWith('/home.html')) {
                 path = path.substring(0, path.length - 'home.html'.length);
            }

            // 3. Remove .html extension from the end (Key fix for Netlify Pretty URLs)
            if (path.endsWith('.html')) {
                path = path.substring(0, path.length - '.html'.length);
            }

            // 4. Remove trailing slash unless it's the root '/'
            if (path !== '/' && path.endsWith('/')) {
                path = path.substring(0, path.length - 1);
            }

            // 5. Ensure root path is consistently just '/' after modifications
            if (path === '') {
                path = '/';
            }

            // 6. Convert to lowercase for case-insensitive comparison (Fix for Netlify)
             path = path.toLowerCase(); // <<< THIS LINE IS NOW ACTIVE

            return path;
        };


        // Normalize the current page's path ONCE
        const normalizedCurrentPath = normalizePath(currentPagePath);

        // Iterate through navigation links
        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (!linkHref || linkHref === '#') return; // Skip non-links or placeholder links

            let linkPath;
            try {
                // Construct absolute URL's path to handle relative paths correctly
                linkPath = new URL(linkHref, window.location.origin).pathname;
            } catch (e) {
                console.warn(`Invalid URL encountered in navigation: ${linkHref}`);
                return; // Skip invalid URLs
            }

            // Normalize the link's path
            const normalizedLinkPath = normalizePath(linkPath);

            // Check for active state using the normalized paths
            if (normalizedCurrentPath === normalizedLinkPath) {
                link.classList.add('active');

                // Traverse up the DOM to add active classes to parent menu items
                let currentElement = link.parentElement; // Start with the LI containing the link
                while (currentElement && currentElement.matches('.main-nav li, .main-nav ul')) {
                    if (currentElement.tagName === 'LI') {
                        currentElement.classList.add('active-ancestor'); // Add class to the parent LI

                        // Find the direct anchor link within that LI (the parent menu item trigger)
                        const parentTriggerLink = currentElement.querySelector(':scope > a');
                        if (parentTriggerLink) {
                             // console.log("Adding 'active' to parent link:", parentTriggerLink); // Optional debug
                            parentTriggerLink.classList.add('active'); // Highlight the trigger link
                        }
                    }
                    // Move up to the parent UL, then its parent LI
                     const parentUl = currentElement.closest('ul.submenu'); // Look specifically for submenu ULs
                     if (parentUl) { // If we are inside a submenu UL
                         currentElement = parentUl.parentElement; // Go to the LI containing this submenu
                     } else {
                         break; // Stop if we reach the main nav UL or something else
                     }
                }
            } // End if active
        }); // End navLinks.forEach


    }; // End initializeHeader

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
     * Orchestrates the loading and initialization of header and footer,
     * loads news, and checks footer position.
     */
    const loadAll = async () => {
        let headerLoaded = false;
        let footerLoaded = false;

        const headerPath = '/_header.html'; // Use root-relative path
        const footerPath = '/_footer.html'; // Use root-relative path

        // --- Load Header ---
        if (headerPlaceholder) {
            headerLoaded = await loadHTML(headerPath, headerPlaceholder);
        }
        // Initialize header AFTER potential loading OR if it exists statically
        if (document.querySelector('.site-header')) {
             initializeHeader();
        } else {
            console.warn("loadAll: .site-header not found after attempting load/checking static.");
        }


        // --- Load Footer ---
        if (footerPlaceholder) {
             footerLoaded = await loadHTML(footerPath, footerPlaceholder);
        }
         // Initialize footer AFTER potential loading OR if it exists statically
         if (document.querySelector('.site-footer')) {
             initializeFooter();
             adjustFooterPosition(); // Adjust position after footer content is known
         } else {
             console.warn("loadAll: .site-footer not found after attempting load/checking static.");
             // Attempt initial adjust anyway in case footer is static but not loaded via placeholder
             adjustFooterPosition();
         }


        // --- Load Latest News ---
        if (typeof loadLatestNews === 'function') {
           await loadLatestNews(); // Load news if container exists on the page
        }


        // --- Final Footer Position Check ---
        if (typeof adjustFooterPosition === 'function') {
            setTimeout(adjustFooterPosition, 100); // Slightly longer delay after potential layout shifts
        }

    }; // End loadAll

    // --- Start Execution ---
    loadAll();

}); // End DOMContentLoaded


// --- Global Event Listeners ---

// Adjust footer position when all resources are loaded (images etc.)
window.addEventListener('load', adjustFooterPosition);

// Adjust footer position on window resize (debounced)
window.addEventListener('resize', debounceFooterAdjust);