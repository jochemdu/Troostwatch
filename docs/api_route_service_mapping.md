# API route naar service mapping (fase 2)

Dit overzicht koppelt elke huidige API-route aan de interne logica die vandaag in de FastAPI-layer zit en de beoogde service-methode die de route na de refactor moet aanroepen. De volgorde volgt de gevraagde prioriteiten.

## Buyers-routes

| Route | Huidige interne logica | Beoogde service-methode |
| --- | --- | --- |
| `GET /buyers` | Haalt een `BuyerRepository` via dependency injection en roept direct `buyers.list_buyers`, dat een repo `.list()` uitvoert. | `buyers.list_buyers()` blijft de centrale service. Route bouwt alleen de dependency-injectie op. |
| `POST /buyers` | Bouwt `BuyerCreateRequest`, roept `buyers.create_buyer` met event-bus publisher en vertaalt `DuplicateBuyerError` naar HTTP 409. | `buyers.create_buyer()` blijft service-entry; route verplaatst foutvertaling naar service-helper `buyers.register_buyer` die een domein-fout teruggeeft i.p.v. HTTP-specifiek. |
| `DELETE /buyers/{label}` | Roept `buyers.delete_buyer` met event-bus publisher. | Nieuwe helper `buyers.remove_buyer()` die delete en event-publicatie encapsuleert; route roept alleen helper en vertaalt uitzonderingen. |

## Lots-/view-routes

| Route | Huidige interne logica | Beoogde service-methode |
| --- | --- | --- |
| `GET /lots` | Vraagt direct `LotRepository.list_lots` met optionele filters voor veilingcode, status en limiet. | Nieuwe `reporting.list_lots_view(repository, auction_code, state, limit)` die filtering en outputvorm verzorgt, zodat de route enkel parameters doorgeeft. |

## Live-control/sync-routes

| Route | Huidige interne logica | Beoogde service-methode |
| --- | --- | --- |
| `POST /sync` | Haalt `db_path` uit config, roept `services.sync_auction` (dat `sync_auction_to_db` in een thread uitvoert) en publiceert optioneel een event. | Nieuwe façade `sync.run_once(db_path, auction_code, auction_url, max_pages, dry_run, publisher)` die configuratie en event-publicatie bevat; route beperkt zich tot request-parse. |
| `POST /live-sync/start` | Maakt `LiveSyncConfig` en roept `LiveSyncRunner.start`, retourneert status/state. | Nieuwe service `live_sync.start(config, runner)` die statusobject vormt en foutvalidatie afhandelt. |
| `POST /live-sync/pause` | Roept `LiveSyncRunner.pause` en geeft status/state terug. | Nieuwe `live_sync.pause(runner)` die consistente payload teruggeeft (status + state). |
| `POST /live-sync/stop` | Roept `LiveSyncRunner.stop` en geeft status/state terug. | Nieuwe `live_sync.stop(runner)` die stop- en statuspayload verzorgt. |
| `GET /live-sync/status` | Roept direct `LiveSyncRunner.get_status`. | Nieuwe `live_sync.status(runner)` zodat route alleen HTTP-respons opbouwt. |

## Overige endpoints

| Route | Huidige interne logica | Beoogde service-methode |
| --- | --- | --- |
| `POST /positions/batch` | Mappt `PositionBatchRequest` naar `PositionUpdateData`, roept `positions.upsert_positions` met event-bus publisher en vertaalt `ValueError` naar HTTP 404. | Nieuwe façade `positions.batch_upsert(updates, repository, publisher)` die validatie/exception-vertaling verzorgt en direct ruwe request-dicts accepteert. |
| `WEBSOCKET /ws/lots` | Abonneert websocket op in-memory `LotEventBus`, houdt loop aan tot disconnect en unsubscribed. | Nieuwe helper `lots_updates.subscribe(websocket, event_bus)` voor subscribe/unsubscribe-loop zodat route enkel verbinding accepteert. |
