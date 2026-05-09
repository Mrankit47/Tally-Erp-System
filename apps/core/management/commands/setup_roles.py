from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Creates default structural Role-Based Access Control (RBAC) groups.'

    def handle(self, *args, **options):
        groups = ['Admin', 'Accountant', 'Manager', 'InventoryManager', 'User', 'Billing Clerk']
        for group in groups:
            created_group, created = Group.objects.get_or_create(name=group)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created security group: {group}'))
            else:
                self.stdout.write(self.style.WARNING(f'Security group already exists: {group}'))
        
        self.stdout.write(self.style.SUCCESS('RBAC structural setup sequence complete.'))
