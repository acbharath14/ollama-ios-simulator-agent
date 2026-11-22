import SwiftUI

struct ContentView: View {
    @State private var tasks: [Task] = [
        Task(title: "Check the welcome screen", notes: "Confirm the title and the Continue button are visible.", done: true),
        Task(title: "Add a new task", notes: "Type a title in the field below and tap Add.", done: false),
        Task(title: "Open a task detail", notes: "Tap a row to see its notes and toggle.", done: false),
        Task(title: "Switch to the About tab", notes: "The second tab shows app info and a counter.", done: false),
        Task(title: "Mark everything done", notes: "Tap the checkmark on each row.", done: false),
    ]
    @State private var newTitle = ""

    var doneCount: Int { tasks.filter { $0.done }.count }

    var body: some View {
        TabView {
            NavigationStack {
                List {
                    Section("Progress") {
                        Text("\(doneCount) of \(tasks.count) done")
                        ProgressView(value: Double(doneCount), total: Double(max(tasks.count, 1)))
                    }
                    Section("Tasks") {
                        ForEach($tasks) { $task in
                            NavigationLink(destination: TaskDetailView(task: $task)) {
                                HStack {
                                    Button(action: { task.done.toggle() }) {
                                        Image(systemName: task.done ? "checkmark.circle.fill" : "circle")
                                    }
                                    .buttonStyle(.plain)
                                    Text(task.title)
                                        .strikethrough(task.done)
                                }
                            }
                        }
                    }
                    Section("Add a task") {
                        HStack {
                            TextField("New task title", text: $newTitle)
                            Button("Add") {
                                let title = newTitle.trimmingCharacters(in: .whitespaces)
                                guard !title.isEmpty else { return }
                                tasks.append(Task(title: title, notes: "Added from the Tasks tab.", done: false))
                                newTitle = ""
                            }
                            .disabled(newTitle.trimmingCharacters(in: .whitespaces).isEmpty)
                        }
                    }
                }
                .navigationTitle("SimSample")
            }
            .tabItem { Label("Tasks", systemImage: "checklist") }

            AboutView()
                .tabItem { Label("About", systemImage: "info.circle") }
        }
    }
}
