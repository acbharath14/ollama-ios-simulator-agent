import SwiftUI

struct TaskDetailView: View {
    @Binding var task: Task

    var body: some View {
        Form {
            Section("Task") {
                Text(task.title).font(.headline)
                Text(task.notes).foregroundStyle(.secondary)
            }
            Section {
                Toggle("Done", isOn: $task.done)
            }
        }
        .navigationTitle("Detail")
        .navigationBarTitleDisplayMode(.inline)
    }
}
