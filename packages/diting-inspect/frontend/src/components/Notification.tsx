const Notification = ({ notification }) => {
	if (!notification) return null;

	return (
		<div
			className={`fixed bottom-4 right-4 p-4 rounded-lg shadow-lg ${notification.type === 'success' ? 'bg-green-500' : 'bg-red-500'
				} text-white`}
		>
			{notification.message}
		</div>
	);
};

export default Notification;
