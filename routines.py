
import asyncio
import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

# Constants
ROUTINES_FILE = Path(__file__).parent / "routines.json"
CLEANUP_AGE_HOURS = 24

class RoutineManager:
    """
    Manages background routines: persistent storage, scheduling, and execution.
    """
    def __init__(self, console: Console, conversations_dir: Path):
        self.console = console
        self.conversations_dir = conversations_dir
        self.routines: List[Dict[str, Any]] = []
        self.load_routines()
        self._running = False

    def load_routines(self) -> None:
        """Load routines from JSON file."""
        if ROUTINES_FILE.exists():
            try:
                content = ROUTINES_FILE.read_text(encoding="utf-8")
                self.routines = json.loads(content)
            except Exception as e:
                self.console.print(f"[red]Error loading routines: {e}[/red]")
                self.routines = []
        else:
            self.routines = []

    def save_routines(self) -> None:
        """Save routines to JSON file."""
        try:
            ROUTINES_FILE.write_text(json.dumps(self.routines, indent=2), encoding="utf-8")
        except Exception as e:
            self.console.print(f"[red]Error saving routines: {e}[/red]")

    def add_routine(self, description: str, time_str: str) -> str:
        """
        Add a new routine.
        time_str format: "HH:MM" (24-hour)
        """
        routine_id = str(uuid.uuid4())[:8]
        new_routine = {
            "id": routine_id,
            "description": description,
            "scheduled_time": time_str, # Daily HH:MM
            "status": "PENDING", # PENDING, RUNNING, COMPLETED, PAUSED, STOPPED
            "created_at": datetime.datetime.now().isoformat(),
            "last_run": None 
        }
        self.routines.append(new_routine)
        self.save_routines()
        return routine_id

    def control_routine(self, routine_id: str, action: str) -> bool:
        """
        Control a routine: pause, resume, stop, delete.
        """
        action = action.lower()
        target = next((r for r in self.routines if r["id"] == routine_id), None)
        
        if not target:
            if action == "delete":
                # Maybe it was already deleted or doesn't exist
                return False
            return False

        if action == "delete":
            self.routines = [r for r in self.routines if r["id"] != routine_id]
            self.save_routines()
            return True
        
        if action == "pause":
            target["status"] = "PAUSED"
        elif action in ("resume", "start"):
            target["status"] = "PENDING"
        elif action == "stop":
            target["status"] = "STOPPED"
        
        self.save_routines()
        return True

    def list_routines(self) -> Table:
        """Return a Rich Table of all routines."""
        t = Table(title="Background Routines", box=box.ROUNDED, border_style="blue")
        t.add_column("ID", style="cyan", no_wrap=True)
        t.add_column("Time", style="green")
        t.add_column("Status", style="white")
        t.add_column("Description", style="white")

        # Sort by status priority (Running > Pending > Paused > Completed)
        # Then by time
        def sort_key(r):
            status_order = {"RUNNING": 0, "PENDING": 1, "PAUSED": 2, "STOPPED": 3, "COMPLETED": 4}
            return (status_order.get(r.get("status", "PENDING"), 5), r.get("scheduled_time", ""))

        sorted_routines = sorted(self.routines, key=sort_key)

        for r in sorted_routines:
            status = r.get("status", "UNKNOWN")
            
            # Color code status
            if status == "PENDING":
                status_style = "[yellow]PENDING[/yellow]"
            elif status == "RUNNING":
                status_style = "[bold green]RUNNING[/bold green]"
            elif status == "COMPLETED":
                status_style = "[dim green]COMPLETED[/dim green]"
            elif status == "PAUSED":
                status_style = "[dim yellow]PAUSED[/dim yellow]"
            elif status == "STOPPED":
                status_style = "[red]STOPPED[/red]"
            else:
                status_style = status

            t.add_row(
                r["id"],
                r["scheduled_time"],
                status_style,
                r["description"]
            )
        
        return t

    def _cleanup_old_tasks(self):
        """Delete COMPLETED tasks older than 24 hours."""
        now = datetime.datetime.now()
        active_routines = []
        changed = False

        for r in self.routines:
            if r.get("status") == "COMPLETED":
                # Check completion time if available? 
                # Our schema didn't strictly track 'completed_at' in the dict above, let's fix that during run.
                # If we don't have completed_at, we might just keep it? 
                # Let's assume user manually deletes or we add timestamp on completion.
                # For now, let's just keep them unless explicitly deleted by user, 
                # OR if we add a completed_at timestamp.
                
                completed_at_str = r.get("completed_at")
                if completed_at_str:
                    try:
                        completed_at = datetime.datetime.fromisoformat(completed_at_str)
                        if (now - completed_at).total_seconds() > (CLEANUP_AGE_HOURS * 3600):
                            changed = True
                            continue # Skip adding this to active_routines (delete)
                    except:
                        pass # Keep if bad date
            
            active_routines.append(r)
        
        if changed:
            self.routines = active_routines
            self.save_routines()

    def start_loop(self, agent_executor):
        """Start the background check loop."""
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._background_loop(agent_executor))

    async def _background_loop(self, agent_executor):
        """
        Infinite loop to check for pending tasks.
        Checks every 30 seconds.
        """
        while self._running:
            try:
                self._cleanup_old_tasks() # Periodic cleanup
                
                now = datetime.datetime.now()
                current_hhmm = now.strftime("%H:%M")
                
                # Check tasks
                # We need to be careful not to run the same task multiple times in the same minute.
                # Usually we might track 'last_run_date' (YYYY-MM-DD).
                # If scheduled for today and not run today, run it.
                
                today_str = now.strftime("%Y-%m-%d")

                for r in self.routines:
                    if r.get("status") == "PENDING":
                        scheduled_time = r.get("scheduled_time", "")
                        last_run_date = r.get("last_run_date")

                        # Catch-up logic: If scheduled time has passed TODAY and it hasn't run yet, run it.
                        # This handles:
                        # 1. Exact match (17:29 == 17:29)
                        # 2. Late start/unblocking (17:29 < 17:31)
                        # We do NOT run if it's tomorrow's task (but our format is just HH:MM, so we assume today)
                        
                        if scheduled_time <= current_hhmm:
                            # Only run if not run today
                            if last_run_date != today_str:
                                # Execute!
                                await self._execute_routine(r, agent_executor, today_str)

            except Exception as e:
                self.console.print(f"[red]Error in background loop: {e}[/red]")
            
            await asyncio.sleep(30) # Check every 30s

    async def _execute_routine(self, routine, agent_executor, today_str):
        """Execute a single routine using the agent."""
        
        # 1. Update status to RUNNING
        routine["status"] = "RUNNING"
        self.save_routines()

        desc = routine.get("description", "")
        
        # self.console.print()
        # self.console.print(Panel(f"[bold yellow]🔔 Background Routine Starting:[/bold yellow] {desc}", border_style="yellow"))

        # Setup Log File
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.conversations_dir / f"routine_{routine['id']}_{timestamp}.txt"
        
        try:
            # 2. Run Agent
            messages = [("human", f"Execute the following background routine task: {desc}")]
            
            # Initial log
            self._append_log(log_file, "USER", f"Execute the following background routine task: {desc}")

            # Stream it so we see progress
            async for event in agent_executor.astream({"messages": messages}, stream_mode="updates"):
                 for node_name, node_data in event.items():
                    if "messages" in node_data:
                        msgs = node_data["messages"]
                        if not isinstance(msgs, list):
                            msgs = [msgs]
                        
                        for m in msgs:
                            # Try to get type and content
                            # LangChain messages usually have .type and .content
                            role = getattr(m, "type", "assistant").upper()
                            content = getattr(m, "content", str(m))
                            self._append_log(log_file, role, content)

            # 3. Mark Complete
            routine["status"] = "COMPLETED"
            routine["last_run_date"] = today_str
            routine["completed_at"] = datetime.datetime.now().isoformat()
            
            # self.console.print(Panel(f"[bold green]✅ Routine Completed:[/bold green] {desc}\n[dim]Log: {log_file.name}[/dim]", border_style="green"))

        except Exception as e:
            self.console.print(f"[red]❌ Routine Failed: {desc} - {e}[/red]")
            self._append_log(log_file, "SYSTEM_ERROR", str(e))
            routine["status"] = "STOPPED" # Stop on failure?
        
        self.save_routines()

    def _append_log(self, filepath: Path, role: str, content: str):
        """Append a message to the log file."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"[{role}]\n{content}\n\n")
        except Exception:
            pass
