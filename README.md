# Notifico!

Notifico is a small open-source ([MIT][]) replacement to the now-defunct
(since 2012) cia.vc service. It relays webhooks from common services to IRC
networks, such as GitHub, JIRA, Gitea, Jenkins, and Bitbucket.

Notifico is/has been used by [CPython][], [FreeBSD][], [Godot][],
[Qutebrowser][], [NASA][], and thousands of other projects.

## Development

### Getting Started

The easiest way to get started with the codebase is with docker:

```shell
git clone https://github.com/TkTech/notifico.git
cd notifico
docker-compose up
```

This will start redis, postgres, IRC bots, and the frontend on port 5000.

## FAQ

### Why doesn't this project use X?

Odds are X (like React or Typescript) didn't exist a decade ago when this
project was created!

### Is this project still maintained?

Yes! The project is currently going through modernization. It has remained
largely unchanged for the last 8-9 years, as IRC and the services feeding into
it are largely stable and unchanging themselves.

[MIT]: http://en.wikipedia.org/wiki/MIT_License
[cpython]: github.com/python/cpython
[FreeBSD]: https://www.freebsd.org/
[godot]: https://godotengine.org/
[qutebrowser]: https://www.qutebrowser.org/
[NASA]: https://nasa.gov