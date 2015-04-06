#!/usr/bin/env python

import click

from mschematool import core


log = core.log


HELP = """Example usage:

$ mschematool default init_db

A database nickname defined in the configuration module must be passed as the first argument.
After it a command must be specified.

"""

@click.group(help=HELP)
@click.option('--config', type=click.Path(exists=True, dir_okay=False), envvar='MSCHEMATOOL_CONFIG', help='Path to configuration module, e.g. "mydir/mschematool_config.py". Environment variable MSCHEMATOOL_CONFIG can be specified instead.', required=True)
@click.option('--verbose/--no-verbose', default=False, help='Print executed SQL/CQL? Default: no.')
@click.argument('dbnick', type=str)
@click.pass_context
def main(ctx, config, verbose, dbnick):
    config_obj = core.Config(verbose, config)
    run_ctx = core.MSchemaTool(config_obj, dbnick)
    ctx.obj = run_ctx

@main.command(help='Creates a DB table used for tracking migrations.')
@click.pass_context
def init_db(ctx):
    ctx.obj.migrations.initialize()

@main.command(help='Show synced migrations.')
@click.pass_context
def synced(ctx):
    migrations = ctx.obj.migrations.fetch_executed_migrations()
    for migration in migrations:
        click.echo(migration)


@main.command(help='Show migrations available for syncing.')
@click.pass_context
def to_sync(ctx):
    migrations = ctx.obj.not_executed_migration_files()
    for migration in migrations:
        click.echo(migration)

@main.command(help='Sync all available migrations.')
@click.pass_context
def sync(ctx):
    to_execute = ctx.obj.not_executed_migration_files()
    if not to_execute:
        click.echo('No migrations to sync')
        return
    for migration_file in to_execute:
        msg = 'Executing %s' % migration_file
        log.info(msg)
        click.echo(msg)
        ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.execute_after_sync()

@main.command(help='Sync a single migration, without syncing older ones.')
@click.argument('migration_file', type=str)
@click.pass_context
def force_sync_single(ctx, migration_file):
    if migration_file in ctx.obj.migrations.fetch_executed_migrations():
        click.echo('This migration is already executed')
        return
    msg = 'Force executing %s' % migration_file
    log.info(msg)
    click.echo(msg)
    ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.execute_after_sync()

@main.command(help='Print a filename for a new migration.')
@click.argument('name', type=str)
@click.argument('migration_type', type=click.Choice(['sql', 'cql', 'py']), default='sql')
@click.pass_context
def print_new(ctx, name, migration_type):
    """Prints filename of a new migration"""
    click.echo(ctx.obj.repository.generate_migration_name(name, migration_type))

@main.command(help='Show latest synced migration.')
@click.pass_context
def latest_synced(ctx):
    migrations = ctx.obj.migrations.fetch_executed_migrations()
    if not migrations:
        click.echo('No synced migrations')
    else:
        click.echo(migrations[-1])

if __name__ == '__main__':
    main()

