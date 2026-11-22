import Foundation

struct Task: Identifiable, Hashable {
    let id = UUID()
    var title: String
    var notes: String
    var done: Bool
}
