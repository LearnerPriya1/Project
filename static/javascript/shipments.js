function toggleDetails(card) {
    var details = card.querySelector('.card-details');
    var toggleButton = card.querySelector('.toggle-button');
    var isExpanded = details.style.display === 'block';

    // Collapse all cards
    var allCards = document.querySelectorAll('.card');
    allCards.forEach(function (c) {
        var cardDetails = c.querySelector('.card-details');
        var cardToggleButton = c.querySelector('.toggle-button');
        if (c !== card) {
            cardDetails.style.display = 'none';
            cardToggleButton.textContent = 'Show Details';
        }
    });

    // Toggle the clicked card's details
    details.style.display = isExpanded ? 'none' : 'block';
    toggleButton.textContent = isExpanded ? 'Show Details' : 'Hide Details';
}