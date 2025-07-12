// Initialize Lucide icons
lucide.createIcons();

// DOM Elements
const loadingSpinner = document.getElementById('loading-spinner');
const loginPage = document.getElementById('login-page');
const registerPage = document.getElementById('register-page');
const dashboardPage = document.getElementById('dashboard-page');
const mainHeader = document.getElementById('main-header');
const mainSidebar = document.getElementById('main-sidebar');

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const logoutButton = document.getElementById('logout-button');
const sidebarToggleButton = document.getElementById('sidebar-toggle');
const sidebarLinks = document.querySelectorAll('.sidebar-link');

const ticketsTableBody = document.getElementById('tickets-table-body');
const chatMessagesContainer = document.getElementById('chat-messages');
const newMessageInput = document.getElementById('new-message-input');
const sendMessageButton = document.getElementById('send-message-button');

let isAuthenticated = false;
let isSidebarOpen = false;

const sampleTickets = [
    { id: 1, title: 'Printer not working', status: 'Open', priority: 'High', assignedTo: 'John Doe', date: '2025-07-01' },
    { id: 2, title: 'Software installation request', status: 'In Progress', priority: 'Normal', assignedTo: 'Jane Smith', date: '2025-06-28' },
    { id: 3, title: 'Network connectivity issue', status: 'Open', priority: 'Critical', assignedTo: 'John Doe', date: '2025-07-02' },
    { id: 4, title: 'Account lockout', status: 'Closed', priority: 'High', assignedTo: 'Jane Smith', date: '2025-06-25' },
    { id: 5, title: 'New user onboarding', status: 'Open', priority: 'Low', assignedTo: 'Admin', date: '2025-07-03' },
];

let chatMessages = [
    { id: 1, sender: 'Support', message: 'Hello! How can I help you today?', time: '10:00 AM' },
    { id: 2, sender: 'You', message: 'Hi, I have an issue with my laptop.', time: '10:02 AM' },
    { id: 3, sender: 'Support', message: 'Please describe the problem in detail.', time: '10:03 AM' },
];

// Sidebar toggle fix for mobile
const toggleSidebar = () => {
    isSidebarOpen = !isSidebarOpen;

    if (isSidebarOpen) {
        mainSidebar.classList.remove('-translate-x-full');
        mainSidebar.classList.add('translate-x-0');

        const overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden';
        overlay.onclick = toggleSidebar;
        document.body.appendChild(overlay);
    } else {
        mainSidebar.classList.remove('translate-x-0');
        mainSidebar.classList.add('-translate-x-full');

        const overlay = document.getElementById('sidebar-overlay');
        if (overlay) overlay.remove();
    }
};

// Sample function for login
const handleLogin = async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    await simulateApiCall('Login');

    if (username === 'user' && password === 'pass') {
        isAuthenticated = true;
        window.location.href = '/dashboard/';
    } else {
        console.error('Login failed: Invalid credentials');
        showCustomMessage('Login Failed', 'Invalid username or password.');
    }
};

const handleRegister = async (e) => {
    e.preventDefault();
    await simulateApiCall('Register');
    showCustomMessage('Registration', 'Registration complete. You can log in now.');
    window.location.href = '/login/';
};

const handleLogout = async () => {
    await simulateApiCall('Logout');
    isAuthenticated = false;
    window.location.href = '/login/';
};

const simulateApiCall = async (action) => {
    loadingSpinner?.classList.remove('hidden');
    await new Promise(resolve => setTimeout(resolve, 1000));
    loadingSpinner?.classList.add('hidden');
};

const showCustomMessage = (title, message) => {
    let modal = document.getElementById('custom-message-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'custom-message-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full text-center">
                <h3 class="text-xl font-bold text-gray-900 mb-4" id="modal-title"></h3>
                <p class="text-gray-700 mb-6" id="modal-message"></p>
                <button class="btn btn-primary" id="modal-close-button">OK</button>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('modal-close-button').onclick = () => modal.classList.add('hidden');
    }
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    modal.classList.remove('hidden');
};

const populateTicketsTable = () => {
    if (!ticketsTableBody) return;
    ticketsTableBody.innerHTML = '';
    sampleTickets.forEach(ticket => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 text-sm font-medium text-gray-900">${ticket.title}</td>
            <td class="px-6 py-4"><span class="badge">${ticket.status}</span></td>
            <td class="px-6 py-4"><span class="badge">${ticket.priority}</span></td>
            <td class="px-6 py-4 text-sm text-gray-700">${ticket.assignedTo}</td>
            <td class="px-6 py-4 text-sm text-gray-400">${ticket.date}</td>
        `;
        ticketsTableBody.appendChild(row);
    });
};

const populateChatMessages = () => {
    if (!chatMessagesContainer) return;
    chatMessagesContainer.innerHTML = '';
    chatMessages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${msg.sender === 'You' ? 'justify-end' : 'justify-start'}`;
        messageDiv.innerHTML = `
            <div class="max-w-[80%] p-3 rounded-lg shadow-sm ${
                msg.sender === 'You'
                    ? 'bg-sky-500 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-900 rounded-bl-none'
            }">
                <p class="text-sm">${msg.message}</p>
                <span class="block text-xs mt-1 ${
                    msg.sender === 'You' ? 'text-sky-100' : 'text-gray-500'
                }">${msg.time}</span>
            </div>
        `;
        chatMessagesContainer.appendChild(messageDiv);
    });
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
};

const handleSendMessage = () => {
    const messageText = newMessageInput.value.trim();
    if (messageText) {
        const newMsg = {
            id: chatMessages.length + 1,
            sender: 'You',
            message: messageText,
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        };
        chatMessages.push(newMsg);
        populateChatMessages();
        newMessageInput.value = '';
    }
};

// DOM Loaded
document.addEventListener('DOMContentLoaded', function () {
    lucide.createIcons();
    isAuthenticated = document.body.contains(dashboardPage);

    if (document.body.classList.contains('login-page-body') || document.body.classList.contains('register-page-body')) {
        mainHeader?.classList.add('hidden');
        mainSidebar?.classList.add('hidden');
    } else if (isAuthenticated) {
        mainHeader?.classList.remove('hidden');
        mainSidebar?.classList.remove('hidden');
        populateTicketsTable();
        populateChatMessages();
    } else {
        mainHeader?.classList.add('hidden');
        mainSidebar?.classList.add('hidden');
    }

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (registerForm) registerForm.addEventListener('submit', handleRegister);
    if (logoutButton) logoutButton.addEventListener('click', handleLogout);
    if (sidebarToggleButton) sidebarToggleButton.addEventListener('click', toggleSidebar);
    if (sendMessageButton) sendMessageButton.addEventListener('click', handleSendMessage);
    if (newMessageInput) {
        newMessageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSendMessage();
        });
    }

    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768 && isSidebarOpen) {
            toggleSidebar(); // Auto-close on desktop resize
        }
    });
});
