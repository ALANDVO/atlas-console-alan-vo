from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import ipaddress
import structlog

from app.models.scope import ScopeEntry, ScopeEntryType, ScopeImportExport
from app.models.user import User

logger = structlog.get_logger()


class ScopeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_entry(
        self,
        entry_type: ScopeEntryType,
        value: str,
        description: Optional[str],
        created_by: int,
    ) -> ScopeEntry:
        """Create a new scope entry."""
        # Validate the entry value based on type
        self._validate_entry(entry_type, value)

        entry = ScopeEntry(
            type=entry_type,
            value=value,
            description=description,
            created_by=created_by,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_entry(self, entry_id: int) -> Optional[ScopeEntry]:
        """Get a scope entry by ID."""
        result = await self.session.execute(
            select(ScopeEntry).where(ScopeEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        entry_type: Optional[ScopeEntryType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[ScopeEntry], int]:
        """List scope entries with optional filters."""
        query = select(ScopeEntry)
        count_query = select(func.count(ScopeEntry.id))

        if entry_type:
            query = query.where(ScopeEntry.type == entry_type)
            count_query = count_query.where(ScopeEntry.type == entry_type)
        if is_active is not None:
            query = query.where(ScopeEntry.is_active == is_active)
            count_query = count_query.where(ScopeEntry.is_active == is_active)

        query = query.order_by(ScopeEntry.created_at.desc()).offset(skip).limit(limit)
        total = (await self.session.execute(count_query)).scalar()
        entries = (await self.session.execute(query)).scalars().all()
        return list(entries), total

    async def update_entry(
        self,
        entry_id: int,
        value: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[ScopeEntry]:
        """Update a scope entry."""
        entry = await self.get_entry(entry_id)
        if not entry:
            return None

        if value is not None:
            self._validate_entry(entry.type, value)
            entry.value = value
        if description is not None:
            entry.description = description
        if is_active is not None:
            entry.is_active = is_active

        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def delete_entry(self, entry_id: int) -> bool:
        """Delete a scope entry."""
        entry = await self.get_entry(entry_id)
        if not entry:
            return False
        await self.session.delete(entry)
        return True

    async def validate_target(self, target: str, target_type: str) -> bool:
        """Validate if a target is within scope."""
        if target_type == "ip":
            return await self._validate_ip(target)
        elif target_type == "port":
            return await self._validate_port(target)
        elif target_type == "service":
            return await self._validate_service(target)
        return False

# Allowed target types: ip, port, service
    async def _validate_ip(self, ip_str: str) -> bool:
        """Validate if an IP is within any active IP range scope entries."""
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False

        entries, _ = await self.list_entries(
            entry_type=ScopeEntryType.IP_RANGE, is_active=True
        )
        for entry in entries:
            try:
                network = ipaddress.ip_network(entry.value, strict=False)
                if ip in network:
                    return True
            except ValueError:
                continue
        return False

    async def _validate_port(self, port_str: str) -> bool:
        """Validate if a port is within any active port range scope entries."""
        try:
            port = int(port_str)
        except ValueError:
            return False

        entries, _ = await self.list_entries(
            entry_type=ScopeEntryType.PORT_RANGE, is_active=True
        )
        for entry in entries:
            if "-" in entry.value:
                start, end = map(int, entry.value.split("-"))
                if start <= port <= end:
                    return True
            else:
                if port == int(entry.value):
                    return True
        return False

    async def _validate_service(self, service: str) -> bool:
        """Validate if a service is in the active service scope entries."""
        entries, _ = await self.list_entries(
            entry_type=ScopeEntryType.SERVICE, is_active=True
        )
        for entry in entries:
            if entry.value.lower() == service.lower():
                return True
        return False

    def _validate_entry(self, entry_type: ScopeEntryType, value: str) -> None:
        """Validate a scope entry value based on its type."""
        if entry_type == ScopeEntryType.IP_RANGE:
            try:
                ipaddress.ip_network(value, strict=False)
            except ValueError:
                raise ValueError(f"Invalid IP range: {value}")
        elif entry_type == ScopeEntryType.PORT_RANGE:
            if "-" in value:
                start, end = map(int, value.split("-"))
                if not (1 <= start <= 65535 and 1 <= end <= 65535 and start <= end):
                    raise ValueError(f"Invalid port range: {value}")
            else:
                port = int(value)
                if not (1 <= port <= 65535):
                    raise ValueError(f"Invalid port: {value}")
        elif entry_type == ScopeEntryType.SERVICE:
            if not value or len(value) > 255:
                raise ValueError(f"Invalid service name: {value}")

    async def import_scope(
        self,
        filename: str,
        format: str,
        data: dict,
        created_by: int,
    ) -> ScopeImportExport:
        """Import scope entries from JSON/YAML data."""
        import_record = ScopeImportExport(
            filename=filename,
            format=format,
            status="pending",
            created_by=created_by,
        )
        self.session.add(import_record)
        await self.session.flush()

        entries_data = data.get("entries", [])
        errors = []
        success_count = 0

        for idx, entry_data in enumerate(entries_data):
            try:
                entry_type = ScopeEntryType(entry_data["type"])
                value = entry_data["value"]
                description = entry_data.get("description")

                self._validate_entry(entry_type, value)
                await self.create_entry(entry_type, value, description, created_by)
                success_count += 1
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})

        import_record.status = "completed" if not errors else "failed"
        import_record.entry_count = success_count
        import_record.error_count = len(errors)
        import_record.errors = str(errors) if errors else None
        await self.session.flush()
        await self.session.refresh(import_record)

        return import_record

    async def export_scope(self, format: str, created_by: int) -> dict:
        """Export all active scope entries."""
        entries, _ = await self.list_entries(is_active=True, limit=10000)
        return {
            "entries": [
                {
                    "type": entry.type.value,
                    "value": entry.value,
                    "description": entry.description,
                }
                for entry in entries
            ]
        }

    async def get_import_export_history(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[ScopeImportExport], int]:
        """Get import/export history."""
        query = select(ScopeImportExport).order_by(
            ScopeImportExport.created_at.desc()
        )
        count_query = select(func.count(ScopeImportExport.id))

        total = (await self.session.execute(count_query)).scalar()
        records = (
            await self.session.execute(query.offset(skip).limit(limit))
        ).scalars().all()
        return list(records), total
