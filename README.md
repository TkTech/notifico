# Notifico!

Notifico takes webhooks from "Providers" (such as Github, JIRA, Gitlab, etc),
filters them based off some configuration, and sends them along to chat
networks like IRC.

Notifico is permissively licensed under the [MIT][] license, and is trivial
to self-host.

## Design

Notifico has a relatively simple design. Users have projects, and projects
have incoming and outgoing channels of messages. Sometimes, you can tack a
service onto one of those channels, such as an IRC logger.

```
┌───────┐
│Project│
├───────┴──────────────────────────────────────────────────────────┐
│                                                                  │
│       ┌─────────────────────┐                                    │
│       │      Sources        │                                    │
│       │  Webhooks, Polling  │                                    │
│       └─────────┬───────────┘                                    │
│                 │                                                │
│                 │                                                │
│  ┌──────────────▼───────────────┐      ┌───────────────────────┐ │
│  │          Channels            └──────►   Channel Services    │ │
│  │  IRC, Discord, Matrix, etc   ◄──────┐  Logging, Relay, etc  │ │
│  └──────────────────────────────┘      └───────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Internally, sources are just an inbound channel. Each Source and Channel is
implemented by a plugin which you can enable, disable, or replace.

## Development

To get started with local development, you can use the docker-compose file
included with the project. If you have Docker and docker-compose installed, a
simple:

```
docker-compose up
```

Will get you up and running. If this is your first time running the container,
make the database and seed the database with required data:

```bash
# Create the database if it's missing.
notifico db init
# Run the latest migrations to get the database schema up to date.
notifico db upgrade
# Seed any missing required data, like core user groups.
notifico seed
# (Optionally) Show all the included plugins
notifico plugins list
# (Optionally) Install some of the plugins
notifico plugins install notifico.plain
```

When upgrading to a new version, or after changing the database models, you'll
need to generate a new migration, review it, and then run the changes:

```bash
# Auto-generate a migration
notifico db migrate
# Review your new migration, then apply it
notifico db upgrade
```

### UX

There's no real "design system" in Notifico, just simple bootstrap5 and a few
conventions around page layout. However, changes to the frontend should keep
a few things in mind:

- All core features should work without JavaScript. Use JavaScript to make
  things progressively better, such as updating background job status live.
- Always use localization for strings presented to users, so that we can
  easily translate Notifico.
- Try your changes at small, medium, and large resolutions. Focus is on
  desktop, but should be usable on a phone. Doesn't need to be great, just
  needs to work.

[MIT]: http://en.wikipedia.org/wiki/MIT_License
