// js/scripts.js

// --- Global Scope Variables and Functions for Footer Positioning ---
let resizeTimerFooter; // Timer variable for debouncing resize

/**
 * Checks page height vs viewport height and sets footer position accordingly.
 * Switches between CSS default (relative) and absolute positioning.
 * Assumes CSS sets body { position: relative; min-height: 100vh; }
 * and .site-footer { position: relative; width: 100%; } as default.
 */
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
        // Fetch the news data
        const response = await fetch(newsDataUrl);
        if (!response.ok) {
            // Throw an error if the fetch fails (e.g., 404 Not Found)
            throw new Error(`HTTP error! status: ${response.status} fetching ${newsDataUrl}`);
        }
        const newsData = await response.json(); // Parse the JSON data

        // Sort data by date descending (newest first) using Date objects
        newsData.sort((a, b) => new Date(b.date) - new Date(a.date));

        // Get the specified number of latest news items
        const latestNews = newsData.slice(0, count);

        // Remove the loading message and clear any previous content
        if (loadingMessage) loadingMessage.remove();
        newsContainer.innerHTML = '';

        // Handle case where no news items are found after fetching/sorting
        if (latestNews.length === 0) {
            newsContainer.innerHTML = '<p style="grid-column: 1 / -1; text-align: center;">Geen nieuwsberichten gevonden.</p>';
            return; // Stop execution for this function
        }

        // Get the current page path to pass as a referrer
        const referrerPath = window.location.pathname;

        // Loop through the latest news items and generate HTML for each
        latestNews.forEach(item => {
            // Format the date for display
            const itemDate = new Date(item.date);
            const formattedDate = itemDate.toLocaleDateString('nl-BE', {
                day: 'numeric', month: 'long', year: 'numeric'
            });

            // Handle image URLs - use placeholder if none, prepend /images/ if relative path
            let finalImageUrl = '/images/placeholder-news.png'; // Default placeholder
            if (item.image) { // Check if image property exists and is not empty
                // Check if it's already a full URL
                if (!item.image.startsWith('http://') && !item.image.startsWith('https://')) {
                    // Assuming relative paths are relative to an /images/ folder at the root
                    finalImageUrl = `/images/${item.image.trim()}`; // Add leading slash and trim whitespace
                } else {
                    finalImageUrl = item.image.trim(); // Use the full URL, trim whitespace
                }
            }

            const summaryText = item.summary || ''; // Ensure summaryText is a string, even if null/undefined
            const itemLink = `/html/nieuws/artikel.html?id=${item.id || ''}&ref=${encodeURIComponent(referrerPath)}`;

            // Use template literals for cleaner HTML construction
            let articleHtml;
            if (summaryText) {
                articleHtml = `
                <article class="news-item" id="latest-${item.id || ''}">
                    <img src="${finalImageUrl}" alt="${item.title || 'Nieuws afbeelding'}" loading="lazy">
                    <div class="news-content">
                        <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                        <h3><a href="${itemLink}">${item.title}</a></h3>
                        <p>${summaryText}</p>
                        <a href="${itemLink}" class="read-more">Lees meer »</a>
                    </div>
                </article>
                `;
            } else {
                 articleHtml = `
                 <article class="news-item" id="latest-${item.id || ''}">
                     <img src="${finalImageUrl}" alt="${item.title || 'Nieuws afbeelding'}" loading="lazy">
                     <div class="news-content">
                         <p class="news-meta">${formattedDate} | ${item.category || 'Algemeen'}</p>
                         <h3><a href="${itemLink}">${item.title}</a></h3>
                         <a href="${itemLink}" class="read-more">Lees meer »</a>
                     </div>
                 </article>
             `;
            }

            newsContainer.insertAdjacentHTML('beforeend', articleHtml);
        });

    } catch (error) {
        // Handle errors during fetch or processing
        console.error('Error loading or processing latest news data:', error);
        const displayError = `<p style="color:red; text-align:center; grid-column: 1 / -1;">Kon laatste nieuws niet laden. (${error.message})</p>`;
        if(loadingMessage) {
            loadingMessage.innerHTML = displayError;
        } else if(newsContainer) {
             newsContainer.innerHTML = displayError;
        }
    }
}


// --- Main Script Logic (Runs after initial HTML is parsed) ---
document.addEventListener('DOMContentLoaded', function() {

    // --- Element Selectors ---
    const headerPlaceholder = document.getElementById('header-placeholder');
    const footerPlaceholder = document.getElementById('footer-placeholder');

    // --- Page Info ---
    // *** IMPORTANT: Adjust 'home.html' if your homepage is index.html or other ***
    const currentPagePath = window.location.pathname; // Get the full path
    let currentPageFilename = currentPagePath.split('/').pop() || 'home.html'; // Default to home.html
    // Handle root case where pop() might be empty
    if (currentPagePath === '/' || currentPagePath.endsWith('/index.html')) {
        currentPageFilename = 'home.html'; // Treat root or index.html as home.html
    }


    // --- Function Definitions within DOMContentLoaded Scope ---

    /**
     * Loads HTML content from a URL into a placeholder element using root-relative paths.
     */
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
        const mainNavUl = document.querySelector('.main-nav > ul'); // Target the main UL directly
        const mobileBreakpoint = 992; // Define mobile breakpoint (MUST match CSS @media query)

        // --- Mobile Menu Toggle Logic ---
        if (menuToggle && mainNavUl) {
            menuToggle.addEventListener('click', () => {
                const isActive = mainNavUl.classList.toggle('active'); // Toggle and check state
                menuToggle.innerHTML = isActive ? '✕' : '☰'; // Update icon
                menuToggle.setAttribute('aria-expanded', isActive); // Update ARIA state

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

        // --- Accordion Logic for Mobile Submenus ---
        const menuItems = mainNavUl.querySelectorAll(':scope > li'); // Select only top-level LIs for accordion trigger

        menuItems.forEach(li => {
            const parentLink = li.querySelector(':scope > a'); // The direct link/text element
            const submenu = li.querySelector(':scope > ul.submenu'); // The direct submenu

            if (parentLink && submenu) {
                 // Set initial ARIA state for accessibility
                 parentLink.setAttribute('aria-haspopup', 'true');
                 parentLink.setAttribute('aria-expanded', 'false'); // Initially closed

                parentLink.addEventListener('click', (event) => {
                    const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';

                    if (isMobileView) {
                        if(parentLink.getAttribute('href') && parentLink.getAttribute('href') !== '#') {
                             event.preventDefault();
                        }

                        // Toggle the current submenu
                        const isOpening = !li.classList.contains('submenu-open');

                         if (isOpening) { // Only close others if we are opening this one
                             li.parentElement.querySelectorAll(':scope > li.submenu-open').forEach(otherLi => {
                                 if (otherLi !== li) { // Don't close the one we just opened
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
                        li.classList.toggle('submenu-open', isOpening); // Use force parameter
                        submenu.classList.toggle('submenu-active', isOpening);
                        parentLink.setAttribute('aria-expanded', isOpening);

                    }
                    // If NOT mobile view, the click should proceed as normal (follow href or do nothing if no href)
                    // Desktop hover effects are handled purely by CSS.
                });

                // Handle nested submenus (if any) - apply same logic recursively or flatly
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

                                 // Optional: Close siblings within the *same* nested level
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

        const normalizePath = (path) => {
            if (!path) return '/'; // Handle cases where path might be undefined/null
            // Treat index.html as root
            if (path.endsWith('/index.html')) {
                path = path.substring(0, path.length - 'index.html'.length);
            }
             // Treat home.html as root
            if (path.endsWith('/home.html')) {
                 path = path.substring(0, path.length - 'home.html'.length);
            }
             // Remove trailing slash unless it's the root
            if (path !== '/' && path.endsWith('/')) {
                path = path.substring(0, path.length - 1);
            }
             // Ensure root path is just '/'
             if (path === '') {
                 path = '/';
             }
            return path;
        };

        const normalizedCurrentPath = normalizePath(currentPagePath); // currentPagePath defined earlier

        navLinks.forEach(link => {
            const linkHref = link.getAttribute('href');
            if (!linkHref || linkHref === '#') return; // Skip non-links or placeholder links

            let linkPath;
            try {
                // Construct absolute URL to handle relative paths correctly
                linkPath = new URL(linkHref, window.location.origin).pathname;
            } catch (e) {
                console.warn(`Invalid URL encountered in navigation: ${linkHref}`);
                return; // Skip invalid URLs
            }

            const normalizedLinkPath = normalizePath(linkPath);

            // Check for active state
            if (normalizedCurrentPath === normalizedLinkPath) {
                link.classList.add('active');

                // Traverse up the DOM to add active classes to parent menu items
                let currentElement = link.parentElement; // Start with the LI containing the link
                while (currentElement && currentElement.matches('.main-nav li, .main-nav ul')) {
                    if (currentElement.tagName === 'LI') {
                         // Add class to the LI itself
                        currentElement.classList.add('active-ancestor');

                         // Find the direct anchor link within that LI (the parent menu item trigger)
                        const parentTriggerLink = currentElement.querySelector(':scope > a');
                        if (parentTriggerLink) {
                            parentTriggerLink.classList.add('active'); // Highlight the trigger link
                             // Optionally expand active ancestors on mobile load (can make menu long)
                             // const isMobileView = window.innerWidth < mobileBreakpoint && getComputedStyle(menuToggle).display !== 'none';
                             // if (isMobileView && currentElement.classList.contains('menu-item-has-children')) { // Assuming you add this class in HTML for items with children
                             //    const submenuToOpen = currentElement.querySelector(':scope > ul.submenu');
                             //    currentElement.classList.add('submenu-open');
                             //    if(submenuToOpen) submenuToOpen.classList.add('submenu-active');
                             //    if(parentTriggerLink) parentTriggerLink.setAttribute('aria-expanded', 'true');
                             // }
                        }
                    }
                    // Move up to the parent UL, then its parent LI
                     const parentUl = currentElement.closest('ul');
                     if (parentUl && parentUl.classList.contains('submenu')) {
                         currentElement = parentUl.parentElement; // Go to the LI containing the submenu
                     } else {
                         break; // Stop if we reach the main nav UL or something else
                     }
                }
            }
        });


    }; // End initializeHeader

    /**
     * Initializes Footer Functionality (Year)
     */
    const initializeFooter = () => {
         const yearSpan = document.getElementById('current-year');
         if (yearSpan) {
             yearSpan.textContent = new Date().getFullYear();
         } else {
             // console.warn("Footer initialization warning: Element with ID 'current-year' not found.");
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
        // Check if the .site-header element is now present in the DOM
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
         // Check if the .site-footer element is now present in the DOM
         if (document.querySelector('.site-footer')) {
             initializeFooter();
             adjustFooterPosition(); // Adjust position after footer content is known
         } else {
             console.warn("loadAll: .site-footer not found after attempting load/checking static.");
             // Attempt initial adjust anyway in case footer is static but not loaded via placeholder
             adjustFooterPosition();
         }


        // --- Load Latest News ---
        // Ensure function exists before calling
        if (typeof loadLatestNews === 'function') {
           await loadLatestNews(); // Load news if container exists on the page
        }


        // --- Final Footer Position Check ---
        // Call again after potential content changes from news load
        if (typeof adjustFooterPosition === 'function') {
            setTimeout(adjustFooterPosition, 100); // Slightly longer delay after potential layout shifts
        }

    }; // End loadAll

    // --- Start Execution ---
    loadAll();

}); // End DOMContentLoaded


// --- Global Event Listeners ---

// Adjust footer position when all resources are loaded (images etc.)
// This is a good final check for layout shifts
window.addEventListener('load', adjustFooterPosition);

// Adjust footer position on window resize (debounced)
window.addEventListener('resize', debounceFooterAdjust);