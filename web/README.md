# Web Interface for Local Scout AI Agent

This directory contains the web interface for the Local Scout AI Agent. The interface is built using HTML, CSS, and JavaScript, with the backend API provided by FastAPI.

## Overview

The web interface allows users to:

- Chat with the AI agent in natural language
- View and manage tasks
- Schedule tasks for execution at specific times
- Monitor task progress in real-time
- View task results and artifacts
- Access task execution history

## Structure

- **templates/**: Contains HTML templates
  - `index.html`: The main application page
- **static/**: Contains static assets
  - **css/**: Stylesheets
    - `styles.css`: Custom styles for the interface
  - **js/**: JavaScript files
    - `main.js`: Main application logic
  - **images/**: Images and icons

## Features

### Real-time Updates

The interface uses WebSockets to receive real-time updates from the agent, including:

- Task status changes
- Task progress updates
- Schedule updates
- New messages in chat

### Task Management

The interface provides comprehensive task management capabilities:

- Create new tasks
- View task details
- Track task progress
- Access task results and artifacts
- Delete tasks

### Scheduling

Users can schedule tasks to run:

- At specific times using cron expressions
- At regular intervals
- Once at a specific date and time
- After a delay

### Responsive Design

The interface is fully responsive and works on devices of all sizes, from mobile phones to desktop computers.

## Technologies

- **HTML5**: Semantic structure
- **CSS3**: Styling with modern features
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript**: Client-side logic
- **WebSockets**: Real-time communication
- **Font Awesome**: Icons

## Theme Support

The interface supports both light and dark themes, which automatically adapt to the user's system preferences but can also be manually toggled.

## Security

All API requests are secured using optional API key authentication, configured in the `.env` file.

## Development

To modify the web interface:

1. Edit the HTML templates in `templates/`
2. Update styles in `static/css/styles.css`
3. Modify client-side logic in `static/js/main.js`

After making changes, restart the server to see the changes.

## Extending

To add new features to the web interface:

1. Add new HTML elements to the templates
2. Add corresponding styles to `styles.css`
3. Implement the logic in `main.js`
4. If needed, add new API endpoints in `api/app.py`