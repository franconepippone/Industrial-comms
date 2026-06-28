from nicegui import ui

columns = [
    {'name': 'time', 'label': 'Time', 'field': 'time'},
    {'name': 'source', 'label': 'Source', 'field': 'source'},
    {'name': 'payload', 'label': 'Payload', 'field': 'payload'},
    {'name': 'type', 'label': 'Type', 'field': 'type'},
]

rows = [
    {'time': '12:00:01', 'source': 'UART1', 'payload': 'HELLO', 'type': 'INFO'},
    {'time': '12:00:02', 'source': 'UART1', 'payload': 'VALUE=42', 'type': 'INFO'},
    {'time': '12:00:03', 'source': 'UART2', 'payload': 'ERROR CRC', 'type': 'ERROR'},
    {'time': '12:00:04', 'source': 'UART1', 'payload': 'WARN TEMP', 'type': 'WARN'},
]

table = ui.table(columns=columns, rows=rows).classes('w-full')

table.add_slot('body', r'''
<q-tr :props="props"
      :style="{
        backgroundColor:
          props.row.type === 'ERROR' ? '#ffd6d6' :
          props.row.type === 'WARN'  ? '#fff3cd' :
          props.row.type === 'INFO'  ? '#e7f1ff' : ''
      }">
  <q-td v-for="col in props.cols" :key="col.name" :props="props">
    {{ col.value }}
  </q-td>
</q-tr>
''')

ui.run()