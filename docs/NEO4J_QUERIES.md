# Neo4j Query Reference

How to run Cypher queries against the Neo4j database from the server.

---

## Quick Reference

### From the Server (inside Docker)

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('YOUR_CYPHER_QUERY_HERE', {})
for r in results: print(r)"
```

### With Parameters

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('MATCH (t:Topic {id: \$id}) RETURN t', {'id': 'fed_policy'})
for r in results: print(r)"
```

---

## Common Queries

### List All Topics

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('MATCH (t:Topic) RETURN t.id as id, t.name as name ORDER BY t.name', {})
for r in results: print(f'{r[\"id\"]}: {r[\"name\"]}')"
```

### Find Topic by Name (partial match)

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('MATCH (t:Topic) WHERE t.name CONTAINS \"LNG\" RETURN t.id, t.name, properties(t) as props', {})
for r in results: print(r)"
```

### Get Topic with All Properties

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('MATCH (t:Topic {id: \"china_lng_price\"}) RETURN properties(t) as props', {})
for r in results: print(r['props'])"
```

### Find Topics with NULL Fields

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('MATCH (t:Topic) WHERE t.name IS NULL OR t.id IS NULL RETURN t', {})
print(f'Found {len(results)} topics with NULL id or name')
for r in results: print(r)"
```

### Count Articles per Topic

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('''
MATCH (t:Topic)
OPTIONAL MATCH (a:Article)-[:ABOUT]->(t)
RETURN t.id as id, t.name as name, count(a) as article_count
ORDER BY article_count DESC
LIMIT 20
''', {})
for r in results: print(f'{r[\"name\"]}: {r[\"article_count\"]} articles')"
```

### Get Recent Topics (created in last 7 days)

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('''
MATCH (t:Topic)
WHERE t.created_at IS NOT NULL AND t.created_at >= datetime() - duration({days: 7})
RETURN t.id, t.name, t.created_at
ORDER BY t.created_at DESC
''', {})
for r in results: print(f'{r[\"id\"]}: {r[\"name\"]} (created: {r[\"created_at\"]})')"
```

### Delete a Topic (CAREFUL!)

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
# First check what will be deleted
results = run_cypher('MATCH (t:Topic {id: \"topic_id_here\"}) RETURN t.name, t.id', {})
print('Will delete:', results)
# Uncomment to actually delete:
# run_cypher('MATCH (t:Topic {id: \"topic_id_here\"}) DETACH DELETE t', {})"
```

---

## Debugging

### Check Neo4j Connection

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
results = run_cypher('RETURN 1 as test', {})
print('Connection OK' if results else 'Connection FAILED')"
```

### Check Graph Stats

```bash
docker exec -w /app/graph-functions apis python -c "
from src.graph.neo4j_client import run_cypher
topics = run_cypher('MATCH (t:Topic) RETURN count(t) as count', {})[0]['count']
articles = run_cypher('MATCH (a:Article) RETURN count(a) as count', {})[0]['count']
rels = run_cypher('MATCH ()-[r]->() RETURN count(r) as count', {})[0]['count']
print(f'Topics: {topics}, Articles: {articles}, Relationships: {rels}')"
```

---

## Notes

- Always use `-w /app/graph-functions` to set the working directory
- The container name is `apis` (check with `docker ps` if different)
- Escape quotes properly in bash: use `\"` inside the Python string
- For complex queries, create a Python script and copy it into the container
