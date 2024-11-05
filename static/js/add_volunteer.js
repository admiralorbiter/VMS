document.addEventListener('DOMContentLoaded', function() {
    initializeSkillsManager();
});

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
        
        skillTag.querySelector('.remove-skill').addEventListener('click', function() {
            skillTag.remove();
            updateSkillsInput();
        });
        
        skillsList.appendChild(skillTag);
        skillInput.value = '';
        updateSkillsInput();
    }

    function updateSkillsInput() {
        const skills = Array.from(skillsList.querySelectorAll('.skill-tag span'))
            .map(span => span.textContent.trim());
        hiddenSkillsInput.value = JSON.stringify(skills);
    }

    addSkillBtn.addEventListener('click', () => addSkill(skillInput.value));
    
    skillInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSkill(skillInput.value);
        }
    });
} 