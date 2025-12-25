// Constants for category data
const categoryNames = {
    'product-launch': '제품 출시',
    'legislation': '규제/정책',
    'earnings': '실적 발표',
    'mna': '인수/합병',
    'other': '기타'
};

const categoryIcons = {
    'product-launch': '🚀',
    'legislation': '📋',
    'earnings': '📊',
    'mna': '🤝',
    'other': '📌'
};

// Initialize months array for 2026
const months = Array.from({ length: 12 }, (_, i) => ({
    month: i + 1,
    year: 2026,
    name: i + 1,
    events: []
}));

let currentFilter = 'all';
let currentSearch = '';
let activeTooltip = null;

// Load events from API
async function loadEventsFromAPI() {
    try {
        document.getElementById('monthsGrid').innerHTML = '<div class="loading">로딩 중...</div>';

        const response = await fetch('http://localhost:5000/api/events');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const events = await response.json();

        months.forEach(month => {
            month.events = events.filter(event => {
                if (!event.date || event.date === 'TBD') {
                    return false;
                }
                const dateParts = event.date.split('-');
                if (dateParts.length === 2) {
                    const year = parseInt(dateParts[0]);
                    const month_num = parseInt(dateParts[1]);

                    if (year === 2026 && month_num >= 1 && month_num <= 12) {
                        return month_num === month.month;
                    }
                }
                return false;
            });
        });

        // Add TBD events to first month
        events.forEach(event => {
            if (!event.date || event.date === 'TBD') {
                months[0].events.push(event);
            }
        });

        renderMonths(currentFilter, currentSearch);
    } catch (error) {
        console.error('Error loading events from API:', error);
        document.getElementById('monthsGrid').innerHTML = '';
        document.getElementById('noResultsMessage').style.display = 'block';
        document.getElementById('noResultsMessage').textContent = `DB Error: ${error.message}`;
    }
}

// Position tooltip near cursor
function positionTooltip(dotElement, tooltip) {
    const rect = dotElement.getBoundingClientRect();
    let left = rect.right + 10;
    let top = rect.top - 10;

    if (left + 350 > window.innerWidth) {
        left = rect.left - 360;
    }
    if (top < 0) {
        top = rect.top;
    }

    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
}

// Render months grid
function renderMonths(filter = 'all', search = '') {
    const monthsGrid = document.getElementById('monthsGrid');
    const noResultsMessage = document.getElementById('noResultsMessage');

    monthsGrid.innerHTML = '';
    noResultsMessage.style.display = 'none';

    let hasResults = false;
    let totalFilteredEvents = 0;

    months.forEach(monthData => {
        const monthCard = document.createElement('div');
        monthCard.className = 'month-card';
        monthCard.dataset.month = monthData.month;

        const monthTitle = document.createElement('div');
        monthTitle.className = 'month-title';
        monthTitle.textContent = `${monthData.year}년 ${monthData.month}월`;

        const eventsContainer = document.createElement('div');
        eventsContainer.className = 'events-in-month';

        let filteredEvents = [...monthData.events];

        if (filter !== 'all') {
            filteredEvents = filteredEvents.filter(e => e.category === filter);
        }

        if (search.trim() !== '') {
            filteredEvents = filteredEvents.filter(e =>
                e.company.toLowerCase().includes(search.toLowerCase()) ||
                e.title.toLowerCase().includes(search.toLowerCase()) ||
                e.description.toLowerCase().includes(search.toLowerCase())
            );
        }

        if (filteredEvents.length === 0) {
            const noEvents = document.createElement('div');
            noEvents.className = 'no-events';
            noEvents.textContent = '';
            eventsContainer.appendChild(noEvents);
        } else {
            hasResults = true;
            totalFilteredEvents += filteredEvents.length;

            filteredEvents.forEach(event => {
                const eventItem = document.createElement('div');
                eventItem.className = 'event-item';

                const eventDot = document.createElement('div');
                eventDot.className = `event-dot ${event.category}`;

                const eventLabel = document.createElement('span');
                eventLabel.className = 'event-label';
                eventLabel.textContent = categoryNames[event.category];

                eventItem.appendChild(eventDot);
                eventItem.appendChild(eventLabel);

                // Tooltip
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.dataset.eventId = Math.random().toString(36).substr(2, 9);

                const statusClass = 'status-' + (event.status || 'pending').toLowerCase().replace(/ /g, '-');
                tooltip.innerHTML = `
                    <div class="tooltip-icon">${categoryIcons[event.category]}</div>
                    <div class="tooltip-title">${event.title || 'No title'}</div>
                    <div class="tooltip-description">${event.description}</div>
                    <div class="tooltip-meta">
                        <span class="tooltip-company">${event.company || 'Unknown'}</span>
                        <span class="tooltip-date">${event.date || 'TBD'}</span>
                        <div class="tooltip-status ${statusClass}">${event.status || 'Pending'}</div>
                    </div>
                `;

                document.getElementById('tooltipContainer').appendChild(tooltip);

                // Tooltip event listeners
                eventDot.addEventListener('mouseenter', function() {
                    if (activeTooltip) {
                        activeTooltip.classList.remove('visible');
                    }
                    tooltip.classList.add('visible');
                    positionTooltip(eventDot, tooltip);
                    activeTooltip = tooltip;
                });

                eventDot.addEventListener('mouseleave', function() {
                    tooltip.classList.remove('visible');
                    if (activeTooltip === tooltip) {
                        activeTooltip = null;
                    }
                });

                eventsContainer.appendChild(eventItem);
            });
        }

        monthCard.appendChild(monthTitle);
        monthCard.appendChild(eventsContainer);
        monthsGrid.appendChild(monthCard);
    });

    if (!hasResults && search.trim() !== '') {
        monthsGrid.style.display = 'none';
        noResultsMessage.style.display = 'block';
    } else {
        monthsGrid.style.display = 'grid';
    }
}

// Event listeners for filters
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentFilter = this.dataset.filter;
        renderMonths(currentFilter, currentSearch);
    });
});

// Event listener for search
document.getElementById('searchInput').addEventListener('input', function() {
    currentSearch = this.value;
    renderMonths(currentFilter, currentSearch);
});

// Event listener for clear button
document.getElementById('searchClear').addEventListener('click', function() {
    document.getElementById('searchInput').value = '';
    currentSearch = '';
    renderMonths(currentFilter, currentSearch);
});

// Update tooltip position on scroll
window.addEventListener('scroll', function() {
    if (activeTooltip) {
        const dotElement = document.querySelector('.event-dot:hover');
        if (dotElement) {
            positionTooltip(dotElement, activeTooltip);
        }
    }
});

// Update tooltip position on resize
window.addEventListener('resize', function() {
    if (activeTooltip) {
        const dotElement = document.querySelector('.event-dot:hover');
        if (dotElement) {
            positionTooltip(dotElement, activeTooltip);
        }
    }
});

// Load events on page load
document.addEventListener('DOMContentLoaded', loadEventsFromAPI);
