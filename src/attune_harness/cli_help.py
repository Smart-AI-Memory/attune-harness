"""Task-first help over the existing command parser and compatibility routes."""

import argparse


class CatalogHelp(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        parser.epilog = self.const
        parser.print_help()
        parser.exit()


def configure_help(parser, commands):
    """Change discovery only; leave registered commands and their contracts intact."""
    descriptions = {entry.dest: entry.help for entry in commands._get_subactions()}
    primary = ('plan', 'build', 'review', 'fix', 'test')
    continuation = ('status', 'resume')
    compatibility = ('review-form', 'inspect-review', 'resume-review',
                     'reconcile-review', 'transfer-review', 'cancel-review')
    advanced = sorted(set(descriptions) - set(primary + continuation + compatibility))

    def section(title, names):
        return title + ':\n' + '\n'.join(
            f'  {name:<19} {descriptions[name]}' for name in names)

    tasks = section('Task execution', primary) + '\n\n' + section('Task controls', continuation)
    hint = 'Use attune-harness COMMAND --help for command options.'
    catalog = '\n\n'.join((
        tasks,
        section('AI tools and integration', advanced),
        section('Compatibility commands (existing scripts)', compatibility),
        'Compatibility commands preserve their original invocation contracts.\n'
        'Use plan/build/review/fix/test and status/resume for new tasks.',
        hint,
    ))
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = (
        'Task verbs are available to people and AI. Specs guide complex work.\n'
        'AI works within accepted scope; people assess evidence at quality gates.'
    )
    parser.usage = '%(prog)s [-h] [--help-all] COMMAND ...'
    parser.epilog = '\n\n'.join((
        tasks,
        'AI tools and integration:\n'
        '  --help-all          Show operational tools and compatibility commands',
        hint,
    ))
    commands.help = argparse.SUPPRESS
    commands.metavar = 'COMMAND'
    parser.add_argument('--help-all', action=CatalogHelp, nargs=0, const=catalog,
                        help='show the complete command catalog and exit')
