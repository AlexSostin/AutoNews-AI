"""
Management command to train the ML quality scorer model.

Usage:
    python manage.py train_quality_model          # Train (requires 50+ articles)
    python manage.py train_quality_model --force   # Train even with less data
    python manage.py train_quality_model --info    # Show current model info
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Train the ML quality scorer model on article engagement data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Train even with less than 50 articles'
        )
        parser.add_argument(
            '--info', action='store_true',
            help='Show current model info without training'
        )

    def handle(self, *args, **options):
        from ai_engine.modules.ml_quality_scorer import train_model, get_model_info

        if options['info']:
            info = get_model_info()
            if info.get('trained'):
                self.stdout.write(self.style.SUCCESS(f"✅ Model trained:"))
                self.stdout.write(f"   Trained at: {info.get('trained_at')}")
                self.stdout.write(f"   Samples: {info.get('samples')}")
                self.stdout.write(f"   CV R²: {info.get('cv_r2_mean', 0):.3f} ± {info.get('cv_r2_std', 0):.3f}")
                self.stdout.write(f"   Top features:")
                for name, imp in (info.get('top_features') or {}).items():
                    self.stdout.write(f"      {name}: {imp:.3f}")
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ No model: {info.get('reason')}"))
            return

        self.stdout.write("🧠 Training ML quality scorer...")
        result = train_model(force=options['force'])

        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(
                f"✅ Model trained on {result['samples']} articles! "
                f"CV R²={result['cv_r2_mean']:.3f}±{result['cv_r2_std']:.3f}"
            ))
            self.stdout.write("   Top features:")
            for name, imp in result.get('top_features', {}).items():
                self.stdout.write(f"      {name}: {imp:.3f}")
        else:
            self.stdout.write(self.style.WARNING(
                f"⚠️ {result.get('reason', 'Training failed')}"
            ))
