from django.core.management.base import BaseCommand
from games.models import RoleTemplate, AbilityTemplate, RoleAbility, Alignment

class Command(BaseCommand):
    help = 'Seeds default roles and abilities'

    def handle(self, *args, **options):
        # Default Alignments
        alignments = [
            ("Town", True),
            ("Mafia", True),
            ("Neutral", True),
        ]
        alignment_objs = {}
        for name, is_default in alignments:
            obj, created = Alignment.objects.get_or_create(name=name)
            obj.is_default = is_default
            obj.save()
            alignment_objs[name.upper()] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created alignment: {name}'))

        # Default Abilities
        abilities = [
            ("Kill", "KILL", "NIGHT", "Eliminate a player during the night."),
            ("Protect", "PROTECT", "NIGHT", "Protect a player from elimination."),
            ("Investigate", "INVESTIGATE", "NIGHT", "Discover a player's alignment."),
            ("Block", "BLOCK", "NIGHT", "Block a player from acting during the night."),
            ("Trap", "TRAP", "NIGHT", "Place a trap that identifies or stops visitors."),
            ("Vote Steal", "VOTE_STEAL", "VOTING", "Steal a target's vote during the voting phase."),
            ("Double Vote", "DOUBLE_VOTE", "VOTING", "Gain an extra vote for yourself or a target during voting."),
            ("Roleblock", "ROLEBLOCK", "NIGHT", "Prevent a player from using their night ability."),
            ("Watch", "LOOKOUT", "NIGHT", "Watch a player and see who visits them."),
            ("Jail", "JAIL", "NIGHT", "Jail a player, protecting and blocking them simultaneously."),
            ("Douse", "DOUSE", "NIGHT", "Douse a player in gasoline for later ignition."),
            ("Ignite", "IGNITE", "NIGHT", "Ignite all doused players, killing them."),
            ("Mafia Kill", "IMMUNE_KILL", "NIGHT", "Kill as the Godfather with investigation immunity."),
        ]

        ability_objs = {}
        for name, atype, phase, desc in abilities:
            obj, created = AbilityTemplate.objects.get_or_create(name=name)
            obj.ability_type = atype
            obj.phase = phase
            obj.description = desc
            obj.is_default = True
            obj.save()
            ability_objs[name] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created ability: {name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated ability to default: {name}'))

        # Default Roles
        roles = [
            ("Villager", "TOWN", "A simple town member with no special abilities."),
            ("Doctor", "TOWN", "Can protect one player each night."),
            ("Sheriff", "TOWN", "Can investigate one player each night."),
            ("Mafioso", "MAFIA", "A member of the mafia who can kill each night."),
            ("Jailor", "TOWN", "A powerful town role who can jail one player each night, protecting and roleblocking them."),
            ("Lookout", "TOWN", "Watches a player at night and sees all visitors."),
            ("Bodyguard", "TOWN", "Can protect someone else or guard themselves once per game."),
            ("Vigilante", "TOWN", "A town member with a gun. Can shoot someone at night (limited use - judge wisely)."),
            ("Godfather", "MAFIA", "The mafia leader. Kills at night and appears as TOWN when investigated."),
            ("Consort", "MAFIA", "A distracting mafia member who roleblocks town power roles."),
            ("Jester", "NEUTRAL", "Wins by getting lynched. Has no abilities - just act suspicious!"),
            ("Executioner", "NEUTRAL", "Wins if a specific town member is lynched. Has no abilities."),
            ("Serial Killer", "NEUTRAL", "A lone killer. Kills anyone each night. Wins by being the last one alive."),
            ("Arsonist", "NEUTRAL", "Douses players in gasoline at night, then ignites all at once. Wins as sole survivor."),
        ]

        role_ability_map = {
            "Doctor": ["Protect"],
            "Sheriff": ["Investigate"],
            "Mafioso": ["Kill"],
            "Jailor": ["Jail"],
            "Lookout": ["Watch"],
            "Bodyguard": ["Protect"],
            "Vigilante": ["Kill"],
            "Godfather": ["Mafia Kill"],
            "Consort": ["Roleblock"],
            "Serial Killer": ["Kill"],
            "Arsonist": ["Douse", "Ignite"],
        }

        for name, align_key, desc in roles:
            role, created = RoleTemplate.objects.get_or_create(name=name, alignment=alignment_objs[align_key])
            role.alignment = alignment_objs[align_key]
            role.description = desc
            role.is_default = True
            role.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated role to default: {name}'))

            # Add abilities
            if name in role_ability_map:
                for ab_name in role_ability_map[name]:
                    RoleAbility.objects.get_or_create(role=role, ability=ability_objs[ab_name])

        # Default Game Template
        from games.models import GameTemplate, GameRoleSlot, PhaseTemplate, WinConditionTemplate

        template, created = GameTemplate.objects.get_or_create(
            name="Classic Mafia",
            defaults={
                "min_players": 4,
                "max_players": 12,
                "is_public": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created default game template: Classic Mafia'))

            # Role slots: 2 Villagers, 1 Doctor, 1 Sheriff, 1 Mafioso
            role_map = {
                "Villager": 2,
                "Doctor": 1,
                "Sheriff": 1,
                "Mafioso": 1,
            }
            for role_name, count in role_map.items():
                role = RoleTemplate.objects.get(name=role_name)
                GameRoleSlot.objects.create(game_template=template, role=role, count=count)

            # Phases
            PhaseTemplate.objects.create(game_template=template, name="Night", phase_type="NIGHT", order=0)
            PhaseTemplate.objects.create(game_template=template, name="Day", phase_type="DAY", order=1)
            PhaseTemplate.objects.create(game_template=template, name="Voting", phase_type="VOTING", order=2)

            # Win conditions
            WinConditionTemplate.objects.create(
                game_template=template,
                name="Town Wins",
                winner_alignment=alignment_objs["TOWN"],
                criteria=[{"type": "ALIGNMENT_COUNT", "target": "MAFIA", "count": 0}],
                order=0,
            )
            WinConditionTemplate.objects.create(
                game_template=template,
                name="Mafia Wins",
                winner_alignment=alignment_objs["MAFIA"],
                criteria=[{"type": "ALIGNMENT_COUNT", "target": "TOWN", "count": 0}],
                order=1,
            )
        else:
            self.stdout.write(self.style.SUCCESS('Default game template already exists, skipping'))

