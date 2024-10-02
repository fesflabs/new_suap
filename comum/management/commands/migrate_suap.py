# coding=utf-8


from django.core.management.commands.migrate import Command as MigrateCommand
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState

original__migrate_all_forwards = MigrationExecutor._migrate_all_forwards


def _migrate_all_forwards(self, state, plan, full_plan, fake, fake_initial):
    """
    Take a list of 2-tuples of the form (migration instance, False) and
    apply them in the order they occur in the full_plan.
    """
    migrations_to_run = {m[0] for m in plan}
    state = ProjectState(real_apps=list(self.loader.unmigrated_apps))
    applied_migrations = {self.loader.graph.nodes[key] for key in self.loader.applied_migrations if key in self.loader.graph.nodes}
    rendered = False
    for migration, _ in full_plan:
        if not migrations_to_run:
            # We remove every migration that we applied from this set so
            # that we can bail out once the last migration has been applied
            # and don't always run until the very end of the migration
            # process.
            break
        if migration in migrations_to_run:
            if 'apps' not in state.__dict__:
                if self.progress_callback and not rendered:
                    self.progress_callback("render_start")
                state.apps  # Render all -- performance critical
                if self.progress_callback and not rendered:
                    rendered = True
                    self.progress_callback("render_success")
            state = self.apply_migration(state, migration, fake=fake, fake_initial=fake_initial)
            migrations_to_run.remove(migration)
        elif migration in applied_migrations:
            if 'apps' in state.__dict__:
                delattr(state, 'apps')
            migration.mutate_state(state, preserve=False)


MigrationExecutor._migrate_all_forwards = _migrate_all_forwards


class Command(MigrateCommand):
    def handle(self, *args, **options):
        print("Este comando foi deprecado, utilizar o migrate")

        # super(Command, self).handle(*args, **options)
