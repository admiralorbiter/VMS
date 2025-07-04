/**
 * Add Volunteer Form JavaScript Module
 * ===================================
 * 
 * This module provides functionality for the volunteer creation form,
 * specifically managing the dynamic skills input system with tag-based
 * interface and form data collection.
 * 
 * Key Features:
 * - Dynamic skills tag management
 * - Add/remove skills with visual tags
 * - Form data collection and submission
 * - Enter key support for quick addition
 * - JSON serialization of skills data
 * - Input validation and cleanup
 * 
 * Skills Management:
 * - Add skills via button click or Enter key
 * - Remove skills via tag close button
 * - Visual tag display with remove functionality
 * - Automatic form data updates
 * - Duplicate prevention (basic)
 * 
 * Form Integration:
 * - Hidden input field for skills data
 * - JSON serialization for server processing
 * - Real-time updates on skills changes
 * - Form submission handling
 * 
 * User Experience:
 * - Visual feedback for added skills
 * - Keyboard support (Enter to add)
 * - Click to remove functionality
 * - Input clearing after addition
 * 
 * Dependencies:
 * - FontAwesome icons for close buttons
 * - Custom CSS for skill tag styling
 * - Bootstrap 5.3.3 for form styling
 * 
 * CSS Classes:
 * - .skill-tag: Individual skill tag styling
 * - .remove-skill: Remove button styling
 * - .skill-input: Skills input field
 * - .add-skill-btn: Add skill button
 * 
 * Form Structure:
 * - #skillsList: Container for skill tags
 * - .skill-input: Input field for new skills
 * - .add-skill-btn: Button to add skills
 * - #skills-data: Hidden input for form data
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSkillsManager();
});

/**
 * Initialize the skills management system
 * Sets up event listeners and form integration
 */
function initializeSkillsManager() {
    const skillsList = document.getElementById('skillsList');
    const skillInput = document.querySelector('.skill-input');
    const addSkillBtn = document.querySelector('.add-skill-btn');
    const form = document.querySelector('.volunteer-form');
    
    // Create hidden input for skills
    const hiddenSkillsInput = document.createElement('input');
    hiddenSkillsInput.type = 'hidden';
    hiddenSkillsInput.name = 'skills';
    hiddenSkillsInput.id = 'skills-data';
    form.appendChild(hiddenSkillsInput);

    /**
     * Add a new skill tag to the list
     * @param {string} skillName - Name of the skill to add
     */
    function addSkill(skillName) {
        if (!skillName.trim()) return;
        
        const skillTag = document.createElement('div');
        skillTag.className = 'skill-tag';
        skillTag.innerHTML = `
            <span>${skillName}</span>
            <button type="button" class="remove-skill">
                <i class="fa-solid fa-times"></i>
            </button>
        `;
        
        // Add remove functionality to the new tag
        skillTag.querySelector('.remove-skill').addEventListener('click', function() {
            skillTag.remove();
            updateSkillsInput();
        });
        
        skillsList.appendChild(skillTag);
        skillInput.value = '';
        updateSkillsInput();
    }

    /**
     * Update the hidden input with current skills data
     * Serializes skills to JSON for form submission
     */
    function updateSkillsInput() {
        const skills = Array.from(skillsList.querySelectorAll('.skill-tag span'))
            .map(span => span.textContent.trim());
        hiddenSkillsInput.value = JSON.stringify(skills);
    }

    // Add skill button event listener
    addSkillBtn.addEventListener('click', () => addSkill(skillInput.value));
    
    // Enter key support for adding skills
    skillInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSkill(skillInput.value);
        }
    });
} 