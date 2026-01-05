import sys
from typing import Optional
from dataclasses import dataclass, field

# Import our modules
from auth import get_drive_service
from drive_client import get_loose_files, get_root_folders, MIME_TYPE_FOLDER
from classifier import FileClassifier, ClassificationResult

@dataclass
class OrganizationPlan:
    folder_assignments: dict = field(default_factory=dict)
    
    # set of folder names that need to be created
    new_folders: set = field(default_factory=set)
    # set of folder names that already exist
    existing_folders: set = field(default_factory=set)

    # add classification result
    def add_result(self, result: ClassificationResult):
        folder = result.suggested_folder
        if folder not in self.folder_assignments:
            self.folder_assignments[folder] = []

        self.folder_assignments[folder].append(result)

        if result.is_new_folder:
            self.new_folders.add(folder)
        else:
            self.existing_folders.add(folder)

    
    # rename folder in plan
    def rename_folder(self, old_name: str, new_name: str):
        if old_name not in self.folder_assignments:
            return False

        files = self.folder_assignments.pop(old_name)

        for result in files:
            result.suggested_folder = new_name
        
        self.folder_assignments[new_name] = files

        if old_name in self.new_folders:
            self.new_folders.removed(old_name)
            self.new_folders.add(new_name)

        return True
    
    # remove file from plan or skip organizing it
    def remove_file(self, file_id: str):
        for folder, files in self.folder_assignments.items():
            for i, result in enumerate(files):
                if result.file_id == file_id:
                    files.pop(i)
                
                    if not files:
                        del self.folder_assignments[folder]
                        self.new_folders.discard(folder)
                    return True
                
        return False
    
    # get summary stats about plan
    def get_summary(self) -> dict:
        total_files = sum(len(files) for files in self.folder_assignments.values())
        return {
            'total_files': total_files,
            'new_folders': len(self.new_folders),
            'existing_folders': len(self.existing_folders),
            'total_folders': len(self.folder_assignments)
        }
    

# display the organization plan in readable format
def display_plan(plan: OrganizationPlan) -> None:
    summary = plan.get_summary()
    
    print("\n" + "=" * 60)
    print(" ORGANIZATION PLAN")
    print("=" * 60)
    print(f"\n  Total files to organize: {summary['total_files']}")
    print(f"  New folders to create:   {summary['new_folders']}")
    print(f"  Existing folders to use: {summary['existing_folders']}")
    print()
    
    # display folders and their files
    sorted_folders = (
        sorted(plan.new_folders) + 
        sorted(plan.existing_folders)
    )
    
    for folder in sorted_folders:
        if folder not in plan.folder_assignments:
            continue
            
        files = plan.folder_assignments[folder]
        is_new = folder in plan.new_folders
        
        # folder header
        icon = "NEW →" if is_new else "📂"
        print(f"  {icon} {folder}")
        
        # list files
        for result in files:
            confidence_icon = {
                'high': '✓',
                'medium': '○',
                'low': '?'
            }.get(result.confidence, '?')
            
            print(f"      {confidence_icon} {result.file_name}")
        
        print() 


# interactive review loop where user can modify the plan
def interactive_review(plan: OrganizationPlan) -> Optional[OrganizationPlan]:
    while True:
        display_plan(plan)
        
        print("-" * 60)
        print(" OPTIONS:")
        print("   [A] Approve and execute this plan")
        print("   [R] Rename a folder")
        print("   [S] Skip a file (remove from plan)")
        print("   [M] Move a file to a different folder")
        print("   [C] Cancel (make no changes)")
        print("-" * 60)
        
        choice = input("\n  Your choice: ").strip().upper()
        
        if choice == 'A':
            confirm = input("  Are you sure you want to proceed? (yes/no): ").strip().lower()
            if confirm == 'yes':
                return plan
            else:
                print("  Okay, returning to review...\n")
                
        elif choice == 'R':
            rename_folder_interactive(plan)
            
        elif choice == 'S':
            skip_file_interactive(plan)
            
        elif choice == 'M':
            move_file_interactive(plan)
            
        elif choice == 'C':
            confirm = input("  Cancel and make no changes? (yes/no): ").strip().lower()
            if confirm == 'yes':
                return None
            
        else:
            print(f"  Unknown option: {choice}")

# handle interactive folder renaming
def rename_folder_interactive(plan: OrganizationPlan) -> None:
    print("\n  Available folders:")
    folders = list(plan.folder_assignments.keys())
    for i, folder in enumerate(folders, 1):
        is_new = "NEW" if folder in plan.new_folders else ""
        print(f"    [{i}] {folder} {is_new}")
    
    try:
        idx = int(input("\n  Enter folder number to rename (0 to cancel): ")) - 1
        if idx == -1:
            return
        if 0 <= idx < len(folders):
            old_name = folders[idx]
            new_name = input(f"  New name for '{old_name}': ").strip()
            if new_name:
                plan.rename_folder(old_name, new_name)
                print(f"Renamed '{old_name}' → '{new_name}'")
            else:
                print("  Cancelled (empty name)")
        else:
            print("  Invalid folder number")
    except ValueError:
        print("  Invalid input")

# handle interactive file skipping
def skip_file_interactive(plan: OrganizationPlan) -> None:
    print("\n  Files in plan:")
    all_files = []
    for folder, files in plan.folder_assignments.items():
        for result in files:
            all_files.append((result, folder))
    
    for i, (result, folder) in enumerate(all_files, 1):
        print(f"    [{i}] {result.file_name} → {folder}")
    
    try:
        idx = int(input("\n  Enter file number to skip (0 to cancel): ")) - 1
        if idx == -1:
            return
        if 0 <= idx < len(all_files):
            result, _ = all_files[idx]
            plan.remove_file(result.file_id)
            print(f"Removed '{result.file_name}' from plan")
        else:
            print("  Invalid file number")
    except ValueError:
        print("  Invalid input")


# handle interactive file moving to diff folder
def move_file_interactive(plan: OrganizationPlan) -> None:
    print("\n  Files in plan:")
    all_files = []
    for folder, files in plan.folder_assignments.items():
        for result in files:
            all_files.append((result, folder))
    
    for i, (result, folder) in enumerate(all_files, 1):
        print(f"    [{i}] {result.file_name} → {folder}")
    
    try:
        idx = int(input("\n  Enter file number to move (0 to cancel): ")) - 1
        if idx == -1:
            return
        if 0 <= idx < len(all_files):
            result, old_folder = all_files[idx]
            
            print(f"\n  Moving: {result.file_name}")
            print(f"  Currently assigned to: {old_folder}")
            print("\n  Available destinations:")
            
            folders = list(plan.folder_assignments.keys())
            for i, folder in enumerate(folders, 1):
                print(f"    [{i}] {folder}")
            print(f"    [N] Create new folder")
            
            dest = input("\n  Destination (number or N): ").strip().upper()
            
            if dest == 'N':
                new_folder = input("  New folder name: ").strip()
                if new_folder:
                    # remove from old location
                    plan.remove_file(result.file_id)
                    # update result and add to new folder
                    result.suggested_folder = new_folder
                    result.is_new_folder = True
                    plan.add_result(result)
                    print(f"  ✓ Moved to new folder '{new_folder}'")
            else:
                try:
                    dest_idx = int(dest) - 1
                    if 0 <= dest_idx < len(folders):
                        dest_folder = folders[dest_idx]
                        # remove from old location
                        plan.remove_file(result.file_id)
                        # update result
                        result.suggested_folder = dest_folder
                        result.is_new_folder = dest_folder in plan.new_folders
                        plan.add_result(result)
                        print(f"  ✓ Moved to '{dest_folder}'")
                    else:
                        print("  Invalid folder number")
                except ValueError:
                    print("  Invalid input")
        else:
            print("  Invalid file number")
    except ValueError:
        print("  Invalid input")


# execute the organization plan
def execute_plan(service, plan: OrganizationPlan, existing_folder_ids: dict) -> None:
    print("\n" + "=" * 60)
    print("EXECUTING PLAN")
    print("=" * 60 + "\n")
    
    # track folder IDs (existing & newly created)
    folder_ids = dict(existing_folder_ids)
    
    # create new folders
    if plan.new_folders:
        print("Creating new folders...")
        for folder_name in plan.new_folders:
            print(f"Creating '{folder_name}'...", end=" ")
            try:
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': MIME_TYPE_FOLDER
                }
                folder = service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                folder_ids[folder_name] = folder.get('id')
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
        print()

        # move files to their folders
        print("Moving files...")
        success_count = 0
        error_count = 0
        
        for folder_name, files in plan.folder_assignments.items():
            folder_id = folder_ids.get(folder_name)
            
            if not folder_id:
                print(f"Skipping '{folder_name}' - folder ID not found")
                continue
            
            for result in files:
                print(f"Moving '{result.file_name}' → {folder_name}...", end=" ")
                try:
                    # get current parents
                    file = service.files().get(
                        fileId=result.file_id,
                        fields='parents'
                    ).execute()
                    
                    previous_parents = ",".join(file.get('parents', []))
                    
                    # move file to new folder
                    service.files().update(
                        fileId=result.file_id,
                        addParents=folder_id,
                        removeParents=previous_parents,
                        fields='id, parents'
                    ).execute()
                    
                    print("✓")
                    success_count += 1
                    
                except Exception as e:
                    print(f"✗ Error: {e}")
                    error_count += 1

        # summary
        print("\n" + "-" * 60)
        print(f" ✓ Successfully moved: {success_count} files")
        if error_count:
            print(f" ✗ Errors: {error_count} files")
        print("-" * 60 + "\n")

# main entry point for drive organizer
def main(use_mock: bool = True, dry_run: bool = False):
    print("=" * 60)
    print(" GOOGLE DRIVE ORGANIZER")
    print("=" * 60 + "\n")
    
    # authentication step
    print("Step 1: Authenticating with Google Drive...")
    print("-" * 40)
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"Authentication failed: {e}")
        return 1
    
    # get existing folders step
    print("Step 2: Scanning existing folders...")
    print("-" * 40)
    folders = get_root_folders(service)
    folder_names = [f['name'] for f in folders]
    folder_ids = {f['name']: f['id'] for f in folders}
    print(f"  Found {len(folders)} top-level folders\n")
    
    # get loose files step
    print("Step 3: Finding loose files...")
    print("-" * 40)
    loose_files = get_loose_files(service)
    
    if not loose_files:
        print(" No loose files found! Your Drive is already organized.")
        return 0
    
    print(f"  Found {len(loose_files)} files to organize\n")
    
    # classify files step
    print("Step 4: Classifying files...")
    print("-" * 40)
    
    mode_str = "mock mode" if use_mock else "AI mode"
    print(f"  Using classifier in {mode_str}\n")
    
    classifier = FileClassifier(use_mock=use_mock)
    results = classifier.classify_multiple(loose_files, folder_names)
    
    # build organization plan step
    print("\nStep 5: Building organization plan...")
    print("-" * 40)
    
    plan = OrganizationPlan()
    for result in results:
        plan.add_result(result)
    
    # review step
    if dry_run:
        display_plan(plan)
        print("\n  [DRY RUN MODE - No changes will be made]\n")
        return 0
    
    # interactive review
    approved_plan = interactive_review(plan)
    
    if approved_plan is None:
        print("\n  Cancelled. No changes were made.\n")
        return 0
    
    # execution step
    execute_plan(service, approved_plan, folder_ids)
    
    print("✨ Organization complete!\n")
    return 0


if __name__ == "__main__":
    # parse simple command line arguments
    use_mock = True  # Default to mock mode
    dry_run = False
    
    if '--ai' in sys.argv:
        use_mock = False
    if '--dry-run' in sys.argv:
        dry_run = True
    if '--read-content' in sys.argv:
        read_content = True
    if '--help' in sys.argv:
        print("""
Google Drive Organizer

Usage: python organizer.py [options]

Options:
    --ai        Use real AI classifier (requires API quota)
    --dry-run   Show plan but don't execute
    --read-content  Read file contents for smarter classification (AI mode only)
    --help      Show this help message

Examples:
    python organizer.py              # Mock mode, interactive
    python organizer.py --dry-run    # Preview what would happen
    python organizer.py --ai         # Use real Gemini AI
    python organizer.py --ai --read-content  # AI + read file contents (smartest)
""")
        sys.exit(0)
    
    sys.exit(main(use_mock=use_mock, dry_run=dry_run))
