# Task Scheduler

The Task Scheduler provides scheduling capabilities for the Local Scout AI Agent. It allows tasks to be executed at specific times, at regular intervals, or triggered by events.

## Features

- **Flexible Scheduling**: Support for cron expressions, intervals, and one-time executions
- **Persistence**: Scheduled tasks survive system reboots
- **Task History**: Tracks task execution history
- **Event Notifications**: Publishes events for task status updates

## Schedule Types

The scheduler supports multiple schedule types:

### Cron Schedules

Cron expressions allow complex scheduling patterns. For example, to run a task every day at 2:30 AM:

```
cron:30 2 * * *
```

The format is: `minute hour day-of-month month day-of-week`

### Interval Schedules

To run a task at regular intervals, use the "every" syntax:

```
every 1h   # Run every hour
every 30m  # Run every 30 minutes
every 1d   # Run every day
```

Supported units: `s` (seconds), `m` (minutes), `h` (hours), `d` (days)

### One-time Schedules

To run a task once at a specific time:

```
at:2023-05-14T14:30:00  # Run at May 14, 2023, 2:30 PM
```

Or to run a task after a delay:

```
in:1h  # Run in 1 hour
in:30m # Run in 30 minutes
```

## Architecture

The scheduler consists of three main components:

1. **TaskScheduler**: The main scheduler class that manages task scheduling
2. **SchedulerPersistence**: Handles persistence of schedules and task execution history
3. **TriggerParser**: Parses schedule specifications into APScheduler triggers

## Usage

### Scheduling a Task

```python
# Create a task
task = AgentTask(
    name="Daily Report",
    description="Generate a daily report"
)
agent.tasks[task.id] = task

# Schedule the task to run every day at midnight
scheduler.schedule_task(task.id, "cron:0 0 * * *")
```

### Cancelling a Schedule

```python
scheduler.cancel_task(task_id)
```

### Getting Schedule Information

```python
schedule = scheduler.get_task_schedule(task_id)
```

### Getting Task Execution History

```python
runs = scheduler.get_task_runs(task_id)
```

## API

The scheduler provides a REST API through the FastAPI application:

- `POST /api/tasks/{task_id}/schedule`: Schedule a task
- `DELETE /api/tasks/{task_id}/schedule`: Cancel a task schedule
- `GET /api/tasks/{task_id}/schedule`: Get a task's schedule
- `GET /api/tasks/{task_id}/runs`: Get a task's execution history
- `GET /api/schedules`: Get all scheduled tasks

## WebSocket Events

The scheduler publishes events through the WebSocket API:

- `schedule_update`: When a task is scheduled
- `schedule_removed`: When a task schedule is cancelled
- `task_started`: When a task execution starts
- `task_finished`: When a task execution completes
- `task_error`: When a task execution fails