"""
Dependency Injection Container

Architecture: Clean separation of concerns via Dependency Inversion Principle (SOLID).

Benefits:
- Testable components (inject mocks)
- Swappable implementations
- Clear dependency graph
- No global state

Usage:
    from app.container import Container
    
    container = Container()
    orbital_engine = container.orbital_engine()

Testing:
    # Override dependencies
    container = Container()
    container.cache.override(MockCache())
    engine = container.orbital_engine()

Standards: Senior-Code (architecture), SOLID principles
"""
from dependency_injector import containers, providers
from app.core.config import get_settings


class Container(containers.DeclarativeContainer):
    """
    Application-wide dependency container.
    
    Manages lifecycle and dependencies of:
    - Configuration
    - External services (Redis, PostgreSQL)
    - Core services (OrbitalEngine, TLEService, etc.)
    - API clients (SpaceX, Celestrak, N2YO, etc.)
    
    Configuration:
        Wire decorators to enable @inject:
        container.wire(modules=[app.api.satellites, app.api.analysis])
    """
    
    # Configuration
    config = providers.Configuration()
    
    # Settings (from environment)
    settings = providers.Singleton(
        get_settings
    )
    
    # Cache (Redis)
    # Note: Actual implementation would need CacheInterface
    # For now, this is a structure example
    # cache = providers.Singleton(
    #     RedisCache,
    #     url=settings.provided.redis_url
    # )
    
    # Database (PostgreSQL)
    # database = providers.Singleton(
    #     Database,
    #     url=settings.provided.database_url
    # )
    
    # Orbital Engine
    # orbital_engine = providers.Factory(
    #     OrbitalEngine,
    #     cache=cache
    # )
    
    # TLE Service
    # tle_service = providers.Singleton(
    #     TLEService,
    #     orbital_engine=orbital_engine,
    #     settings=settings
    # )
    
    # External API clients
    # spacex_client = providers.Singleton(SpaceXClient)
    # launch_library_client = providers.Singleton(LaunchLibrary2Client)
    # celestrak_client = providers.Singleton(CelestrakFallback)
    # n2yo_client = providers.Singleton(N2YOClient)


# Global container instance
container = Container()


# Example interfaces for future implementation
class CacheInterface:
    """Interface for cache implementations."""
    
    async def get(self, key: str) -> any:
        """Get value from cache."""
        raise NotImplementedError
    
    async def set(self, key: str, value: any, ttl: int = None):
        """Set value in cache."""
        raise NotImplementedError
    
    async def delete(self, key: str):
        """Delete key from cache."""
        raise NotImplementedError


class DatabaseInterface:
    """Interface for database implementations."""
    
    async def execute(self, query: str, params: dict = None):
        """Execute query."""
        raise NotImplementedError
    
    async def fetch_one(self, query: str, params: dict = None):
        """Fetch single row."""
        raise NotImplementedError
    
    async def fetch_all(self, query: str, params: dict = None):
        """Fetch all rows."""
        raise NotImplementedError


# Migration Guide
"""
To migrate existing code to use DI:

1. Define interfaces (e.g., CacheInterface above)

2. Update service constructors to accept interfaces:
    class OrbitalEngine:
        def __init__(self, cache: CacheInterface):
            self.cache = cache

3. Register in container:
    orbital_engine = providers.Factory(
        OrbitalEngine,
        cache=cache
    )

4. Use @inject in API routes:
    from dependency_injector.wiring import inject, Provide
    
    @router.get("/satellites")
    @inject
    async def get_satellites(
        engine: OrbitalEngine = Depends(Provide[Container.orbital_engine])
    ):
        return await engine.get_positions()

5. Override in tests:
    @pytest.fixture
    def container():
        container = Container()
        container.cache.override(MockCache())
        yield container
        container.unwire()
"""
